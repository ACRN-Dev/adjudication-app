"""
Monitor/QC Portal API
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models.monitor import MonitorRecord, MonitorImportBatch, ReconciliationItem, MonitorAuditEvent
from models.canonical import (
    Participant, SubjectAssignment, AuditEvent, AdjudicationStatus,
    AdjudicationVisit, AdjudicationRecord, ReviewerRole,
)
from models.longitudinal import LongitudinalParticipant, ReviewerAssignment, VisitInstance
from models.auth import PortalUser
from services.monitor_security import (
    MonitorIdentity, identity, scope, scan_blinding,
    validate_import, qc_gate, assignment_gate, release_gate, audit,
)

router = APIRouter()


class Action(BaseModel):
    study_code: str
    reason: str = Field(min_length=3)
    payload: dict = {}


class AssignRequest(BaseModel):
    reviewer_a_upn: str = Field(min_length=3)
    reviewer_b_upn: str = Field(min_length=3)
    due_date: Optional[datetime] = None
    target_cases: Optional[int] = None
    reason: str = Field(min_length=5)


def ser(x):
    return {c.name: getattr(x, c.name) for c in x.__table__.columns}


def seed(db):
    if db.query(MonitorRecord).filter_by(is_demo=True).first():
        if not db.query(Participant).first():
            participant = Participant(
                subject_id="ADJ-DEMO-001",
                case_number="ADJ-DEMO-001",
                site_code="ZWE001",
                study="PROTECT-Africa",
                status=AdjudicationStatus.IN_REVIEW,
                qc_approved=True,
                visit_count=2,
            )
            db.add(participant)
            db.flush()
            db.add_all([
                AdjudicationVisit(participant_id=participant.id, visit_number=1, visit_code="V01", status="IN_REVIEW"),
                AdjudicationVisit(participant_id=participant.id, visit_number=2, visit_code="V02", status="PENDING"),
            ])
            db.commit()
        return
    now = datetime.utcnow()
    cases = [
        ("CASE", "PROTECT-Africa", "ZWE001-0292", "Reconciliation Required",
         {"country": "Zimbabwe", "site": "Site ZW-01", "trigger": "DV-30",
          "packet_score": 72, "queries": 1, "due": "06 Aug 2026"}),
        ("CASE", "PROTECT-Africa", "ZWE001-0443", "Pre-QC",
         {"country": "Zimbabwe", "site": "Site ZW-01", "trigger": "DV-30",
          "packet_score": 94, "queries": 0, "due": "05 Aug 2026"}),
        ("QUERY", "PROTECT-Africa", "ZWE001-0292", "Overdue",
         {"query_id": "Q-DEMO-014", "category": "Missing evidence",
          "wording": "Provide timed repeat BP source record", "due": "01 Aug 2026"}),
        ("ASSIGNMENT", "LOPE-Nigeria", "NGA004-0118", "Overdue",
         {"reviewer": "Reviewer A", "opened": True, "signed": False,
          "due": "30 Jul 2026", "decision_content": "WITHHELD"}),
        ("RECUSAL", "PROTECT-Africa", "ZWE001-0520", "Reassignment Required",
         {"reason_category": "Site conflict", "replacement": "Pending"}),
        ("DISCORDANCE", "PROTECT-Africa", "ZWE001-0611", "Committee Review",
         {"fields": ["Diagnosis", "Certainty"], "route": "Committee",
          "decision_content": "WITHHELD UNTIL PERMITTED POINT"}),
        ("FINAL_QC", "PROTECT-Africa", "ZWE001-0704", "Awaiting Final QC",
         {"reviewers_signed": True, "committee_locked": True, "dv27_respected": True}),
        ("RELEASE", "LOPE-Nigeria", "NGA004-0088", "Ready for Release",
         {"final_qc": "Pass", "destination": "eTMF placeholder", "checksum": "sha256:demo-ready"}),
        ("TRANSFER", "PROTECT-Africa", "ZWE001-0801", "Failed",
         {"destination": "eTMF placeholder", "last_attempt": "02 Aug 2026",
          "error": "Synthetic connection timeout"}),
        ("RELEASE", "PROTECT-Africa", "ZWE001-0102", "Released",
         {"final_qc": "Pass", "release_version": 1, "checksum": "sha256:demo-released",
          "locked": True}),
    ]
    for typ, study, case, status, payload in cases:
        db.add(MonitorRecord(
            record_type=typ, study_code=study, case_id=case, status=status,
            payload=payload, owner_upn="monitor.demo@acrnhealth.com",
            due_at=now + timedelta(days=2), locked=(status == "Released"), is_demo=True,
        ))
    db.add_all([
        MonitorImportBatch(
            batch_id="BATCH-DEMO-001", study_code="PROTECT-Africa", source_type="EDC",
            filename="protect_edc_demo.csv", checksum="demo-ok", file_size=48120,
            mapping_version="MAP-PROTECT-2.1", row_count=120, participant_count=24,
            validation_result="Passed", blinding_result="Passed", status="Complete",
            imported_by="coordinator.demo@acrnhealth.com", is_demo=True,
        ),
        MonitorImportBatch(
            batch_id="BATCH-DEMO-002", study_code="LOPE-Nigeria", source_type="eSource",
            filename="lope_biomarker_demo.csv", checksum="demo-quarantine", file_size=9012,
            mapping_version="MAP-LOPE-1.1", row_count=12, participant_count=3,
            validation_result="Failed", blinding_result="Prohibited field detected",
            status="Unblinding Quarantine", error_summary="Synthetic PlGF header detected",
            imported_by="coordinator.demo@acrnhealth.com", is_demo=True,
        ),
    ])
    db.add(ReconciliationItem(
        study_code="PROTECT-Africa", case_id="ZWE001-0292", canonical_field="systolic_bp",
        edc_value="162", esource_value="168", canonical_value="168", source_used="eSource",
        discrepancy_category="VALUE_DISCREPANCY", clinically_meaningful=True,
        resolution_history=[{"value": "162/168 preserved",
                             "reason": "Repeat source reading confirmed", "by": "monitor.demo"}],
        is_demo=True,
    ))
    participant = Participant(
        subject_id="ADJ-DEMO-001",
        case_number="ADJ-DEMO-001",
        site_code="ZWE001",
        study="PROTECT-Africa",
        status=AdjudicationStatus.IN_REVIEW,
        qc_approved=True,
        visit_count=2,
    )
    db.add(participant)
    db.flush()
    db.add_all([
        AdjudicationVisit(participant_id=participant.id, visit_number=1, visit_code="V01", status="IN_REVIEW"),
        AdjudicationVisit(participant_id=participant.id, visit_number=2, visit_code="V02", status="PENDING"),
    ])
    db.commit()


# ── Existing demo dashboard / list / action endpoints ─────────────────────────

@router.get("/me")
def me(i: MonitorIdentity = Depends(identity)):
    return {"upn": i.upn, "role": i.role, "studies": i.studies,
            "clinical_decision_authority": False, "in_flight_decision_content": False, "demo": True}


@router.get("/dashboard")
def dashboard(i: MonitorIdentity = Depends(identity), db: Session = Depends(get_db)):
    seed(db)
    rows = db.query(MonitorRecord).filter_by(is_demo=True).all()
    visible = [r for r in rows if not i.studies or "*" in i.studies or r.study_code in i.studies]
    counts: dict = {}
    for r in visible:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {
        "demo": True, "counts": counts,
        "performance": {
            "median_import_to_qc": "1.8 days", "median_adjudicator_turnaround": "3.2 days",
            "median_query_response": "2.4 days", "agreement_rate": "84%",
            "cohens_kappa": "0.78", "dv27_capped": 2, "release_backlog": 1,
        },
        "notifications": [
            "1 blinding quarantine requires QA review",
            "1 overdue reviewer assignment",
            "1 transfer failed",
        ],
    }


@router.get("/operational-dashboard")
def operational_dashboard(
    study: Optional[str] = None,
    site: Optional[str] = None,
    adjudicator: Optional[str] = None,
    status: Optional[str] = None,
    visit: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    """Visit-level operational dashboard for assignment and adjudication progress."""
    seed(db)
    participant_query = db.query(Participant)
    if i.studies and "*" not in i.studies:
        participant_query = participant_query.filter(Participant.study.in_([s for s in i.studies if s]))
    if study:
        participant_query = participant_query.filter(Participant.study == study)
    if site:
        participant_query = participant_query.filter(Participant.site_code == site)
    if date_from:
        participant_query = participant_query.filter(Participant.created_at >= date_from)
    if date_to:
        participant_query = participant_query.filter(Participant.created_at <= date_to)

    participant_ids = [p.id for p in participant_query.all()]
    if not participant_ids:
        empty = {
            "summary": {
                "available_participants": 0,
                "available_visits": 0,
                "assigned_visits": 0,
                "pending_visits": 0,
                "completed_visits": 0,
                "overdue_visits": 0,
                "concordant_visits": 0,
                "discordant_visits": 0,
                "escalated_visits": 0,
                "awaiting_reviewer_c": 0,
                "awaiting_committee_review": 0,
                "overall_completion_pct": 0,
                "target_progress_pct": 0,
            },
            "by_status": {},
            "by_study": {},
            "by_site": {},
            "adjudicators": [],
            "items": [],
            "filters": {"studies": [], "sites": [], "adjudicators": [], "statuses": []},
        }
        return empty
    participant_by_id = {p.id: p for p in db.query(Participant).filter(Participant.id.in_(participant_ids)).all()}

    visit_query = db.query(AdjudicationVisit).join(Participant, AdjudicationVisit.participant_id == Participant.id).filter(
        AdjudicationVisit.participant_id.in_(participant_ids)
    )
    if visit:
        visit_query = visit_query.filter(AdjudicationVisit.visit_code == visit)
    if date_from:
        visit_query = visit_query.filter(AdjudicationVisit.visit_date >= date_from)
    if date_to:
        visit_query = visit_query.filter(AdjudicationVisit.visit_date <= date_to)
    adjudication_visits = visit_query.order_by(AdjudicationVisit.visit_date.asc(), AdjudicationVisit.visit_number.asc()).all()
    visits = []
    seen_visit_keys = set()
    for adjudication_visit in adjudication_visits:
        key = (adjudication_visit.participant_id, adjudication_visit.visit_number)
        seen_visit_keys.add(key)
        visits.append({
            "participant_id": adjudication_visit.participant_id,
            "visit_id": adjudication_visit.id,
            "visit_number": adjudication_visit.visit_number,
            "visit_code": adjudication_visit.visit_code,
            "visit_date": adjudication_visit.visit_date,
            "status": adjudication_visit.status,
            "resolution_type": adjudication_visit.resolution_type,
            "finalized_at": adjudication_visit.finalized_at,
            "created_at": adjudication_visit.created_at,
            "source": "adjudication",
        })

    canonical_by_case = {
        (p.case_number or p.subject_id): p
        for p in participant_by_id.values()
        if p.case_number or p.subject_id
    }
    canonical_by_subject = {
        p.subject_id: p
        for p in participant_by_id.values()
        if p.subject_id
    }
    longitudinal_query = db.query(LongitudinalParticipant)
    if i.studies and "*" not in i.studies:
        longitudinal_query = longitudinal_query.filter(LongitudinalParticipant.study.in_([s for s in i.studies if s]))
    if study:
        longitudinal_query = longitudinal_query.filter(LongitudinalParticipant.study == study)
    if site:
        longitudinal_query = longitudinal_query.filter(LongitudinalParticipant.site_code == site)
    longitudinal_rows = longitudinal_query.all()
    longitudinal_by_id = {lp.id: lp for lp in longitudinal_rows}
    for lp in longitudinal_rows:
        participant = canonical_by_case.get(lp.blinded_subject_id) or canonical_by_subject.get(lp.blinded_subject_id)
        if not participant:
            continue
        rt_visit_query = db.query(VisitInstance).filter_by(participant_id=lp.id, superseded=False)
        if visit:
            rt_visit_query = rt_visit_query.filter(VisitInstance.scheduled_visit_code == visit)
        if date_from:
            rt_visit_query = rt_visit_query.filter(VisitInstance.visit_datetime >= date_from)
        if date_to:
            rt_visit_query = rt_visit_query.filter(VisitInstance.visit_datetime <= date_to)
        for index, rt_visit in enumerate(rt_visit_query.order_by(VisitInstance.visit_sequence.asc(), VisitInstance.visit_datetime.asc()).all(), start=1):
            visit_number = rt_visit.visit_sequence or index
            key = (participant.id, visit_number)
            if key in seen_visit_keys:
                continue
            visits.append({
                "participant_id": participant.id,
                "visit_id": None,
                "visit_number": visit_number,
                "visit_code": rt_visit.scheduled_visit_code or f"V{visit_number:02d}",
                "visit_date": rt_visit.visit_datetime,
                "status": "PENDING",
                "resolution_type": None,
                "finalized_at": None,
                "created_at": rt_visit.visit_datetime or lp.created_at,
                "source": "realtime",
            })

    if adjudicator:
        assignment_ids = []
        for assignment in db.query(SubjectAssignment).filter(
            or_(
                SubjectAssignment.reviewer_a_upn == adjudicator,
                SubjectAssignment.reviewer_b_upn == adjudicator,
                SubjectAssignment.reviewer_c_upn == adjudicator,
            )
        ).all():
            assignment_ids.append(assignment.participant_id)
        if assignment_ids:
            visits = [v for v in visits if v["participant_id"] in assignment_ids]
        else:
            visits = []

    if status:
        status_key = status.upper()
        visits = [v for v in visits if (v["status"] or "PENDING").upper() == status_key]

    complete_statuses = {"COMPLETED", "FINALIZED", "LOCKED", "CLOSED", "CONCORDANT", "DISCORDANT", "THREE_WAY_DIVERGENT"}
    current_time = datetime.utcnow()
    by_status: dict[str, int] = {}
    by_study: dict[str, int] = {}
    by_site: dict[str, int] = {}
    adjudicator_summary: dict[str, dict] = {}
    items: list[dict] = []
    total_assigned_visits = 0
    completed_visits = 0
    pending_visits = 0
    overdue_visits = 0
    concordant_visits = 0
    discordant_visits = 0
    escalated_visits = 0
    awaiting_reviewer_c = 0
    awaiting_committee_review = 0

    all_assignments = {a.participant_id: a for a in db.query(SubjectAssignment).filter(SubjectAssignment.participant_id.in_(participant_ids)).all()}

    rt_assignments: dict = {}
    if longitudinal_by_id:
        for rt_assignment in db.query(ReviewerAssignment).filter(ReviewerAssignment.participant_id.in_(list(longitudinal_by_id))).all():
            lp = longitudinal_by_id.get(rt_assignment.participant_id)
            participant = (canonical_by_case.get(lp.blinded_subject_id) or canonical_by_subject.get(lp.blinded_subject_id)) if lp else None
            if participant:
                rt_assignments.setdefault(participant.id, []).append(rt_assignment)

    for visit in visits:
        participant = participant_by_id.get(visit["participant_id"])
        if not participant:
            continue
        assignment = all_assignments.get(visit["participant_id"])
        status_key = (visit["status"] or "PENDING").upper()
        by_status[status_key] = by_status.get(status_key, 0) + 1
        by_study[str(participant.study)] = by_study.get(str(participant.study), 0) + 1
        by_site[(participant.site_code or "UNKNOWN")] = by_site.get((participant.site_code or "UNKNOWN"), 0) + 1

        adjudicators = []
        if assignment:
            for upn in [assignment.reviewer_a_upn, assignment.reviewer_b_upn, assignment.reviewer_c_upn]:
                if upn:
                    adjudicators.append(upn.lower())
            if assignment.due_date and assignment.due_date < current_time and status_key not in complete_statuses:
                overdue_visits += 1
            if assignment.status in {"ACTIVE", "ASSIGNED"}:
                total_assigned_visits += 1
        elif rt_assignments.get(participant.id):
            adjudicators = [a.reviewer_upn.lower() for a in rt_assignments[participant.id] if a.reviewer_upn]
            total_assigned_visits += 1

        if status_key in complete_statuses:
            completed_visits += 1
        else:
            pending_visits += 1

        if status_key in {"FINALIZED", "LOCKED", "CLOSED", "CONCORDANT"} or (visit["resolution_type"] and visit["resolution_type"].upper() in {"CONCORDANT", "CONCORDANT_A_EQUALS_B"}):
            concordant_visits += 1
        if status_key in {"DISCORDANT", "THREE_WAY_DIVERGENT"} or (visit["resolution_type"] and visit["resolution_type"].upper() in {"DISCORDANT", "THREE_WAY_DIVERGENT"}):
            discordant_visits += 1

        reviewer_c_signed = db.query(AdjudicationRecord).filter(
            AdjudicationRecord.visit_id == visit["visit_id"],
            AdjudicationRecord.reviewer_role == ReviewerRole.REVIEWER_C,
            AdjudicationRecord.signed.is_(True),
        ).first() if visit["visit_id"] else None
        has_reviewer_c = bool((assignment and assignment.reviewer_c_upn) or any(a.reviewer_role == "REVIEWER_C" for a in rt_assignments.get(participant.id, [])))
        if has_reviewer_c and not reviewer_c_signed:
            awaiting_reviewer_c += 1
        if status_key in {"DISCORDANT", "THREE_WAY_DIVERGENT", "COMMITTEE_PENDING"}:
            awaiting_committee_review += 1
        if has_reviewer_c:
            escalated_visits += 1

        item_adjudicators = []
        for upn in adjudicators:
            item_adjudicators.append(upn)
            summary = adjudicator_summary.setdefault(upn, {"assigned_visits": 0, "completed_visits": 0, "pending_visits": 0, "overdue_visits": 0, "periods": {}})
            summary["assigned_visits"] += 1
            if status_key in complete_statuses:
                summary["completed_visits"] += 1
            else:
                summary["pending_visits"] += 1
            if assignment and assignment.due_date and assignment.due_date < current_time and status_key not in complete_statuses:
                summary["overdue_visits"] += 1
            period_label = assignment.assigned_at.strftime("%Y-%m") if assignment and assignment.assigned_at else "unassigned"
            summary["periods"][period_label] = summary["periods"].get(period_label, 0) + 1

        items.append({
            "subject_id": participant.subject_id,
            "study": str(participant.study),
            "site_code": participant.site_code or "UNKNOWN",
            "visit_code": visit["visit_code"],
            "visit_number": visit["visit_number"],
            "status": status_key,
            "adjudicators": item_adjudicators,
            "updated_at": (visit["finalized_at"] or visit["created_at"]).isoformat() if visit["created_at"] else None,
            "is_overdue": bool(assignment and assignment.due_date and assignment.due_date < current_time and status_key not in complete_statuses),
            "open_work_url": "/monitor/patients",
        })

    all_studies = sorted({str(p.study) for p in participant_by_id.values()})
    all_sites = sorted({p.site_code or "UNKNOWN" for p in participant_by_id.values()})
    all_adjudicators = sorted({upn for entry in adjudicator_summary for upn in [entry]})
    if not all_adjudicators:
        all_adjudicators = sorted({
            upn for assignment in db.query(SubjectAssignment).filter(SubjectAssignment.participant_id.in_(participant_ids)).all()
            for upn in [assignment.reviewer_a_upn, assignment.reviewer_b_upn, assignment.reviewer_c_upn] if upn
        })

    completion_pct = round((completed_visits / len(visits) * 100), 1) if visits else 0
    target_progress_pct = 0
    if total_assigned_visits:
        target_progress_pct = round((completed_visits / max(total_assigned_visits, 1)) * 100, 1)

    adjudicator_rows = []
    for upn, summary in sorted(adjudicator_summary.items()):
        adjudicator_rows.append({
            "adjudicator_upn": upn,
            "assigned_visits": summary["assigned_visits"],
            "completed_visits": summary["completed_visits"],
            "pending_visits": summary["pending_visits"],
            "overdue_visits": summary["overdue_visits"],
            "completion_pct": round((summary["completed_visits"] / max(summary["assigned_visits"], 1)) * 100, 1),
            "periods": summary["periods"],
        })

    return {
        "summary": {
            "available_participants": len(participant_by_id),
            "available_visits": len(visits),
            "assigned_visits": total_assigned_visits,
            "pending_visits": pending_visits,
            "completed_visits": completed_visits,
            "overdue_visits": overdue_visits,
            "concordant_visits": concordant_visits,
            "discordant_visits": discordant_visits,
            "escalated_visits": escalated_visits,
            "awaiting_reviewer_c": awaiting_reviewer_c,
            "awaiting_committee_review": awaiting_committee_review,
            "overall_completion_pct": completion_pct,
            "target_progress_pct": target_progress_pct,
        },
        "by_status": dict(sorted(by_status.items())),
        "by_study": dict(sorted(by_study.items())),
        "by_site": dict(sorted(by_site.items())),
        "adjudicators": adjudicator_rows,
        "items": items,
        "filters": {
            "studies": all_studies,
            "sites": all_sites,
            "adjudicators": all_adjudicators,
            "statuses": sorted({(v["status"] or "PENDING").upper() for v in visits}),
        },
    }


@router.post("/blinding/scan")
def blinding(req: Action, i: MonitorIdentity = Depends(identity), db: Session = Depends(get_db)):
    scope(i, req.study_code)
    result = scan_blinding(req.payload.get("names", []), req.payload.get("content", ""))
    audit(db, i, "BLINDING_SCAN", "IMPORT", req.payload.get("filename", "demo"),
          req.study_code, req.reason, result,
          "SUCCESS" if result["passed"] else "QUARANTINED")
    db.commit()
    return result


# ── New QC-approve and assign endpoints ───────────────────────────────────────

@router.post("/qc-approve/{subject_id}")
def qc_approve(
    subject_id: str,
    reason: str = "QC review passed",
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    """
    Monitor approves a subject for adjudicator assignment.
    Sets qc_approved=True on the Participant record and writes an audit entry.
    Subjects that are not QC-approved cannot be assigned to adjudicators.
    """
    participant = (
        db.query(Participant)
        .filter(
            (Participant.subject_id == subject_id) |
            (Participant.case_number == subject_id)
        )
        .first()
    )
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    if participant.qc_approved:
        return {
            "status": "already_approved",
            "subject_id": subject_id,
            "case_number": participant.case_number,
            "qc_approved": True,
        }

    participant.qc_approved = True
    db.add(AuditEvent(
        event_type="QC_APPROVED",
        participant_id=participant.id,
        actor_upn=i.upn,
        actor_role=i.role,
        description=f"Monitor QC approval granted for {subject_id}",
        event_metadata={"reason": reason},
        timestamp=datetime.utcnow(),
    ))
    db.commit()
    return {
        "status": "approved",
        "subject_id": subject_id,
        "case_number": participant.case_number,
        "qc_approved": True,
        "approved_by": i.upn,
    }


@router.post("/assign/{subject_id}")
def assign_adjudicators(
    subject_id: str,
    req: AssignRequest,
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    """
    Assign Reviewer A and Reviewer B to a QC-approved subject.
    Enforces:
      - Subject must be QC-approved first (qc_approved=True)
      - Reviewer A UPN != Reviewer B UPN
      - Both reviewers must have ADJUDICATOR role in PortalUser
      - No existing active assignment (one assignment per subject)
    Creates a SubjectAssignment record for adjudicator stickiness.
    """
    participant = (
        db.query(Participant)
        .filter(
            (Participant.subject_id == subject_id) |
            (Participant.case_number == subject_id)
        )
        .first()
    )
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    # QC gate
    if not participant.qc_approved:
        raise HTTPException(
            status_code=409,
            detail=f"Subject {subject_id} has not been QC-approved. "
                   f"Run /api/monitor/qc-approve/{subject_id} first.",
        )

    # A ≠ B
    a_upn = req.reviewer_a_upn.strip().lower()
    b_upn = req.reviewer_b_upn.strip().lower()
    if a_upn == b_upn:
        raise HTTPException(
            status_code=409,
            detail="Reviewer A and Reviewer B must be different people.",
        )

    # Both must be ADJUDICATOR role
    for upn, label in [(a_upn, "Reviewer A"), (b_upn, "Reviewer B")]:
        user = db.query(PortalUser).filter_by(email=upn, status="ACTIVE").first()
        if not user:
            raise HTTPException(
                status_code=422,
                detail=f"{label} ({upn}) does not have an active ACRN portal account.",
            )
        if user.role != "ADJUDICATOR":
            raise HTTPException(
                status_code=422,
                detail=f"{label} ({upn}) does not hold ADJUDICATOR role (role={user.role}).",
            )

    # No duplicate assignment
    existing = db.query(SubjectAssignment).filter_by(participant_id=participant.id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Subject {subject_id} already has an active assignment "
                   f"(A={existing.reviewer_a_upn}, B={existing.reviewer_b_upn}).",
        )

    assignment = SubjectAssignment(
        participant_id=participant.id,
        reviewer_a_upn=a_upn,
        reviewer_b_upn=b_upn,
        assigned_by=i.upn,
        due_date=req.due_date,
        target_cases=req.target_cases,
        status="ACTIVE",
    )
    db.add(assignment)

    db.add(AuditEvent(
        event_type="ADJUDICATOR_ASSIGNED",
        participant_id=participant.id,
        actor_upn=i.upn,
        actor_role=i.role,
        description=(
            f"Assigned reviewer_a={a_upn}, reviewer_b={b_upn} "
            f"to case {subject_id}"
        ),
        event_metadata={
            "reviewer_a": a_upn,
            "reviewer_b": b_upn,
            "due_date": req.due_date.isoformat() if req.due_date else None,
            "target_cases": req.target_cases,
            "reason": req.reason,
        },
        timestamp=datetime.utcnow(),
    ))
    db.commit()

    return {
        "status": "assigned",
        "subject_id": subject_id,
        "case_number": participant.case_number,
        "reviewer_a": a_upn,
        "reviewer_b": b_upn,
        "due_date": req.due_date.isoformat() if req.due_date else None,
        "assigned_by": i.upn,
    }


@router.get("/assignments")
def list_assignments(
    status: str = "ACTIVE",
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    """
    List all subject assignments with reviewer progress (Monitor view).
    """
    from models.canonical import AdjudicationRecord, ReviewerRole
    assignments = db.query(SubjectAssignment).filter_by(status=status).all()
    rows = []
    for a in assignments:
        p = db.get(Participant, a.participant_id)
        # Count signed records per reviewer
        recs = (
            db.query(AdjudicationRecord)
            .filter_by(participant_id=a.participant_id, signed=True)
            .all()
        )
        signed_a = sum(1 for r in recs if r.reviewer_upn == a.reviewer_a_upn)
        signed_b = sum(1 for r in recs if r.reviewer_upn == a.reviewer_b_upn)
        rows.append({
            "assignment_id": a.id,
            "subject_id": p.subject_id if p else None,
            "case_number": p.case_number if p else None,
            "reviewer_a": a.reviewer_a_upn,
            "reviewer_b": a.reviewer_b_upn,
            "reviewer_c": a.reviewer_c_upn,
            "visits_assigned": p.visit_count if p else 0,
            "signed_a": signed_a,
            "signed_b": signed_b,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "status": a.status,
        })
    return {"items": rows, "total": len(rows)}


# ── Original list / action endpoints (preserved) ─────────────────────────────

@router.get("/{kind}")
def list_kind(
    kind: str,
    study_code: str = "",
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    seed(db)
    scope(i, study_code) if study_code else None
    if kind == "imports":
        rows = db.query(MonitorImportBatch).filter_by(is_demo=True).all()
    elif kind == "reconciliation":
        rows = db.query(ReconciliationItem).filter_by(is_demo=True).all()
    elif kind == "audit":
        rows = db.query(MonitorAuditEvent).filter_by(is_demo=True).all()
    else:
        rows = db.query(MonitorRecord).filter_by(is_demo=True).all()
    return {
        "demo": True,
        "items": [
            ser(r) for r in rows
            if (not hasattr(r, "study_code") or not i.studies or
                "*" in i.studies or r.study_code in i.studies)
            and (not study_code or r.study_code == study_code)
        ],
    }


@router.post("/{kind}/{entity_id}/action")
def act(
    kind: str,
    entity_id: str,
    req: Action,
    i: MonitorIdentity = Depends(identity),
    db: Session = Depends(get_db),
):
    scope(i, req.study_code)
    action = req.payload.get("action", "").upper()
    if action == "PRE_QC_RELEASE":
        qc_gate(req.payload.get("items", []))
    if action == "ASSIGN":
        assignment_gate(
            req.payload.get("reviewer_a"),
            req.payload.get("reviewer_b"),
            set(req.payload.get("eligible", [])),
        )
    if action in {"APPROVE_RELEASE", "TRANSFER"}:
        release_gate(req.payload.get("final_qc"), req.payload.get("committee_locked", True))
    row = db.get(MonitorRecord, entity_id)
    if row and row.locked:
        raise HTTPException(
            409, "Released or locked records are immutable; create a corrected replacement version"
        )
    audit(db, i, action or f"{kind.upper()}_ACTION", kind, entity_id,
          req.study_code, req.reason, req.payload)
    db.commit()
    return {"demo": True, "status": "accepted", "clinical_decision_changed": False}

