"""
Assignment API — Target-based adjudicator allocation and progress tracking
==========================================================================
Endpoints:
  POST /api/assignment/targets    — set per-reviewer target case count for the current period
  GET  /api/assignment/progress   — per-reviewer progress vs target

Access: MONITOR, ADMIN only.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.canonical import SubjectAssignment, AdjudicationRecord, ReviewerRole
from models.auth import PortalUser
from services.auth_service import require_role

router = APIRouter()


class ReviewerTarget(BaseModel):
    reviewer_upn: str = Field(min_length=3)
    target_cases: int = Field(ge=1, description="Target number of cases for this period")
    period_label: Optional[str] = None     # e.g. "2026-Q3"
    due_date: Optional[datetime] = None


class SetTargetsRequest(BaseModel):
    targets: List[ReviewerTarget]
    set_by: Optional[str] = "system"


@router.post("/targets")
def set_reviewer_targets(
    req: SetTargetsRequest,
    db: Session = Depends(get_db),
    user: PortalUser = Depends(require_role("MONITOR", "ADMIN")),
):
    """
    Set per-reviewer case-count targets for a batch period.
    Updates the target_cases and due_date on all active assignments for each reviewer.
    Returns summary of how many assignments were updated.
    """
    updated = []
    for t in req.targets:
        assignments = (
            db.query(SubjectAssignment)
            .filter(
                (SubjectAssignment.reviewer_a_upn == t.reviewer_upn) |
                (SubjectAssignment.reviewer_b_upn == t.reviewer_upn)
            )
            .filter_by(status="ACTIVE")
            .all()
        )
        count = 0
        for a in assignments:
            a.target_cases = t.target_cases
            if t.due_date:
                a.due_date = t.due_date
            count += 1
        updated.append({
            "reviewer_upn": t.reviewer_upn,
            "target_cases": t.target_cases,
            "assignments_updated": count,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        })

    db.commit()
    return {
        "status": "success",
        "set_by": req.set_by or user.email,
        "updated": updated,
    }


@router.get("/progress")
def reviewer_progress(
    db: Session = Depends(get_db),
    user: PortalUser = Depends(require_role("MONITOR", "ADMIN")),
):
    """
    Per-reviewer progress view: assigned cases, signed cases, remaining, and target.
    """
    # Collect all active assignments
    assignments = db.query(SubjectAssignment).filter_by(status="ACTIVE").all()

    # Build per-reviewer tallies
    tallies: dict[str, dict] = {}

    def _ensure(upn: str):
        if upn not in tallies:
            tallies[upn] = {
                "reviewer_upn": upn,
                "assigned_as_a": 0,
                "assigned_as_b": 0,
                "signed_a": 0,
                "signed_b": 0,
                "target_cases": None,
                "due_date": None,
            }

    for a in assignments:
        _ensure(a.reviewer_a_upn)
        _ensure(a.reviewer_b_upn)
        tallies[a.reviewer_a_upn]["assigned_as_a"] += 1
        tallies[a.reviewer_b_upn]["assigned_as_b"] += 1
        if a.target_cases is not None:
            tallies[a.reviewer_a_upn]["target_cases"] = a.target_cases
            tallies[a.reviewer_b_upn]["target_cases"] = a.target_cases
        if a.due_date:
            tallies[a.reviewer_a_upn]["due_date"] = a.due_date.isoformat()
            tallies[a.reviewer_b_upn]["due_date"] = a.due_date.isoformat()

    # Count signed records per reviewer per role
    all_signed = (
        db.query(AdjudicationRecord)
        .filter_by(signed=True)
        .filter(AdjudicationRecord.reviewer_role.in_([
            ReviewerRole.REVIEWER_A, ReviewerRole.REVIEWER_B
        ]))
        .all()
    )
    for r in all_signed:
        upn = r.reviewer_upn
        _ensure(upn)
        if r.reviewer_role == ReviewerRole.REVIEWER_A:
            tallies[upn]["signed_a"] += 1
        elif r.reviewer_role == ReviewerRole.REVIEWER_B:
            tallies[upn]["signed_b"] += 1

    # Compute totals and remaining
    progress = []
    for upn, t in tallies.items():
        total_assigned = t["assigned_as_a"] + t["assigned_as_b"]
        total_signed = t["signed_a"] + t["signed_b"]
        remaining = total_assigned - total_signed
        pct = round(total_signed / total_assigned * 100, 1) if total_assigned else 0.0
        target = t["target_cases"]
        vs_target = (total_signed - target) if target is not None else None
        progress.append({
            "reviewer_upn": upn,
            "total_assigned": total_assigned,
            "total_signed": total_signed,
            "remaining": remaining,
            "completion_pct": pct,
            "target_cases": target,
            "cases_vs_target": vs_target,
            "due_date": t["due_date"],
            "on_track": (vs_target >= 0) if vs_target is not None else None,
        })

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "reviewers": sorted(progress, key=lambda x: x["reviewer_upn"]),
    }
