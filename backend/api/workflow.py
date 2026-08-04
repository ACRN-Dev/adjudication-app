"""
ACRN Workflow API — /api/workflow
================================
Workflow gates, state transitions, reviewer isolation, and concordance endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from database import get_db, DB_OFFLINE
from services.workflow_policy import (
    WorkflowState,
    check_qa_release_gate,
    check_reviewer_gate,
    check_reviewer_isolation,
    check_committee_quorum,
    check_transfer_authority,
    check_signing_gate,
    evaluate_concordance
)

router = APIRouter()


class QAReleaseRequest(BaseModel):
    qa_officer_id: str
    comments: Optional[str] = None


class TransitionRequest(BaseModel):
    actor_role: str
    target_state: str
    comments: Optional[str] = None


class ConcordanceRequest(BaseModel):
    submission_a: Dict[str, Any]
    submission_b: Dict[str, Any]


@router.post("/{subject_id}/qa-release")
def qa_release(subject_id: str, req: QAReleaseRequest):
    """QA officer releases an evidence packet for dual adjudication."""
    gate = check_qa_release_gate("PENDING", True)
    if not gate.allowed:
        raise HTTPException(status_code=400, detail=gate.reason)

    return {
        "subject_id": subject_id,
        "status": "success",
        "gate_result": "ALLOWED",
        "new_state": WorkflowState.QA_RELEASED.value,
        "released_by": req.qa_officer_id,
        "released_at": datetime.utcnow().isoformat(),
        "message": gate.reason,
    }


@router.get("/{subject_id}/state")
def get_workflow_state(subject_id: str):
    """Retrieve current workflow state and allowed actions."""
    return {
        "subject_id": subject_id,
        "current_state": WorkflowState.QA_RELEASED.value,
        "allowed_transitions": [
            WorkflowState.REVIEWER_A_SUBMITTED.value,
            WorkflowState.REVIEWER_B_SUBMITTED.value,
        ],
        "qa_cleared": True,
        "blinding_active": True,
    }


@router.post("/{subject_id}/transition")
def attempt_transition(subject_id: str, req: TransitionRequest):
    """Attempt a state transition with governance gate checks."""
    try:
        target = WorkflowState(req.target_state.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {req.target_state}")

    auth_gate = check_transfer_authority(req.actor_role, target)
    if not auth_gate.allowed:
        raise HTTPException(status_code=403, detail=auth_gate.reason)

    return {
        "subject_id": subject_id,
        "previous_state": "QA_RELEASED",
        "new_state": target.value,
        "transitioned_by": req.actor_role,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success",
    }


@router.get("/{subject_id}/reviewer-view")
def get_reviewer_view(subject_id: str, requesting_reviewer: str, target_reviewer: str):
    """Check reviewer isolation access control."""
    can_see = check_reviewer_isolation(requesting_reviewer, target_reviewer, "QA_RELEASED")
    return {
        "subject_id": subject_id,
        "requesting_reviewer": requesting_reviewer,
        "target_reviewer": target_reviewer,
        "can_view_target_submission": can_see,
        "reason": "Unblinded only after both reviewers submit or during committee review (SOP-ADJ-002)." if not can_see else "Access granted."
    }


@router.post("/{subject_id}/concordance")
def check_concordance(subject_id: str, req: ConcordanceRequest):
    """Evaluate concordance between Reviewer A and Reviewer B submissions."""
    res = evaluate_concordance(req.submission_a, req.submission_b)
    return {
        "subject_id": subject_id,
        "concordance": res,
        "evaluated_at": datetime.utcnow().isoformat(),
    }
