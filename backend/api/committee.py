"""
Committee Review API — POST /api/committee/{subject_id}/lock & Reviewer C adjudication
Chair consensus arbitration for discordant cases and Reviewer C 3rd independent outcome (OAC Charter §10).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import hashlib
from services.case_finalization import finalize_case_pdf, record_determination_activity

from database import get_db
from models.canonical import (
    Participant, AdjudicationVisit, AdjudicationRecord, CommitteeDecision, SubjectAssignment, AuditEvent, ReviewerRole,
    DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus
)

router = APIRouter()


class ReviewerCSubmissionRequest(BaseModel):
    reviewer_upn: str
    reviewer_name: Optional[str] = "Reviewer C"
    diagnosis: DiagnosisCode
    date_of_diagnosis: Optional[datetime] = None
    onset_class: OnsetClass
    severity: SeverityGrade
    certainty: CertaintyLevel
    rationale: str = Field(min_length=5, description="Mandatory clinical rationale")
    comment: Optional[str] = None
    other_rationale: Optional[str] = None
    visit_number: int = 1


class CommitteeLockRequest(BaseModel):
    adopted_reviewer: Optional[ReviewerRole] = ReviewerRole.CHAIR
    final_diagnosis: DiagnosisCode
    date_of_diagnosis: Optional[datetime] = None
    final_onset_class: OnsetClass
    final_severity: SeverityGrade
    final_certainty: CertaintyLevel
    chair_rationale: str = Field(min_length=5)
    chair_upn: str
    chair_name: str
    quorum_met: bool = True
    members_present: int = 3
    visit_number: int = 1


@router.get("/discordant-cases")
def list_discordant_cases(db: Session = Depends(get_db)):
    participants = db.query(Participant).filter(
        Participant.status.in_([
            AdjudicationStatus.DISCORDANT,
            AdjudicationStatus.COMMITTEE_PENDING,
            AdjudicationStatus.THREE_WAY_DIVERGENT
        ])
    ).all()
    results = []
    for p in participants:
        records = db.query(AdjudicationRecord).filter_by(participant_id=p.id).all()
        rec_a = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_A), None)
        rec_b = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_B), None)
        rec_c = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_C), None)
        results.append({
            "id": str(p.id),
            "subject_id": p.subject_id,
            "case_number": p.case_number,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "reviewer_a": {
                "diagnosis": rec_a.diagnosis.value if rec_a and rec_a.diagnosis else None,
                "certainty": rec_a.certainty.value if rec_a and rec_a.certainty else None,
                "rationale": rec_a.rationale if rec_a else None,
            } if rec_a else None,
            "reviewer_b": {
                "diagnosis": rec_b.diagnosis.value if rec_b and rec_b.diagnosis else None,
                "certainty": rec_b.certainty.value if rec_b and rec_b.certainty else None,
                "rationale": rec_b.rationale if rec_b else None,
            } if rec_b else None,
            "reviewer_c": {
                "diagnosis": rec_c.diagnosis.value if rec_c and rec_c.diagnosis else None,
                "certainty": rec_c.certainty.value if rec_c and rec_c.certainty else None,
                "rationale": rec_c.rationale if rec_c else None,
            } if rec_c else None,
        })
    return {"items": results, "total": len(results), "discordant_cases": results}



@router.post("/{subject_id}/reviewer-c")
def submit_reviewer_c(subject_id: str, req: ReviewerCSubmissionRequest, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    visit = db.query(AdjudicationVisit).filter_by(
        participant_id=participant.id, visit_number=req.visit_number
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="The subject visit does not exist.")

    records = db.query(AdjudicationRecord).filter_by(visit_id=visit.id).all()
    rec_a = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_A), None)
    rec_b = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_B), None)
    if not rec_a or not rec_b or not rec_a.signed or not rec_b.signed:
        raise HTTPException(status_code=409, detail="Reviewer C is available only after both A and B have signed this visit.")
    if rec_a.diagnosis == rec_b.diagnosis:
        raise HTTPException(status_code=409, detail="Reviewer A and B agree; Reviewer C escalation is not permitted.")
    if req.diagnosis == DiagnosisCode.OTHER and (not req.other_rationale or not req.other_rationale.strip()):
        raise HTTPException(status_code=422, detail="other_rationale is mandatory when Reviewer C selects Other.")

    # Reviewer C must be different from both A and B
    assignment = db.query(SubjectAssignment).filter_by(participant_id=participant.id).first()
    if assignment:
        a_upn = assignment.reviewer_a_upn.strip().lower()
        b_upn = assignment.reviewer_b_upn.strip().lower()
        c_upn = req.reviewer_upn.strip().lower()
        if assignment.reviewer_c_upn and c_upn != assignment.reviewer_c_upn.strip().lower():
            raise HTTPException(
                status_code=403,
                detail=f"Reviewer C is assigned to {assignment.reviewer_c_upn}; this case cannot be submitted by another adjudicator.",
            )
        if c_upn == a_upn:
            raise HTTPException(
                status_code=409,
                detail=f"Reviewer C ({req.reviewer_upn}) is the same person as Reviewer A. "
                       f"OAC Charter §10 requires an independent third reviewer.",
            )
        if c_upn == b_upn:
            raise HTTPException(
                status_code=409,
                detail=f"Reviewer C ({req.reviewer_upn}) is the same person as Reviewer B. "
                       f"OAC Charter §10 requires an independent third reviewer.",
            )
        # Record the reviewer C UPN in the assignment for future reference
        assignment.reviewer_c_upn = c_upn

    # Check concordance with A and B
    diag_a = rec_a.diagnosis if rec_a else None
    diag_b = rec_b.diagnosis if rec_b else None
    matches_a = req.diagnosis == diag_a
    matches_b = req.diagnosis == diag_b

    is_three_way_divergent = not (matches_a or matches_b)

    # Save Reviewer C record
    rec_c = db.query(AdjudicationRecord).filter_by(
        visit_id=visit.id, reviewer_role=ReviewerRole.REVIEWER_C
    ).first()
    if not rec_c:
        rec_c = AdjudicationRecord(
            participant_id=participant.id,
            visit_id=visit.id,
            reviewer_role=ReviewerRole.REVIEWER_C,
            reviewer_upn=req.reviewer_upn,
            reviewer_name=req.reviewer_name,
            visit_number=req.visit_number,
        )
        db.add(rec_c)

    rec_c.diagnosis = req.diagnosis
    rec_c.date_of_diagnosis = req.date_of_diagnosis
    rec_c.onset_class = req.onset_class
    rec_c.severity = req.severity
    rec_c.certainty = req.certainty
    rec_c.rationale = req.rationale
    rec_c.comment = req.comment
    rec_c.other_rationale = req.other_rationale.strip() if req.other_rationale else None
    rec_c.signed = True
    rec_c.signed_at = datetime.utcnow()
    rec_c.signature_hash = hashlib.sha256(
        f"{subject_id}|{req.reviewer_upn}|{req.diagnosis.value}|{req.visit_number}|{rec_c.signed_at.isoformat()}".encode()
    ).hexdigest()
    record_determination_activity(db, participant, visit, rec_c)

    if is_three_way_divergent:
        participant.status = AdjudicationStatus.FINALIZED
        concordance_state = "RESOLVED_BY_REVIEWER_C"
    else:
        participant.status = AdjudicationStatus.RESOLVED_BY_MAJORITY
        concordance_state = "CONCORDANT_WITH_A" if matches_a else "CONCORDANT_WITH_B"

    # Audit event for Reviewer C submission
    db.add(AuditEvent(
        event_type="REVIEWER_C_SIGNED",
        participant_id=participant.id,
        actor_upn=req.reviewer_upn,
        actor_role="REVIEWER_C",
        description=(
            f"Reviewer C submitted: {req.diagnosis.value} / "
            f"certainty={req.certainty.value} / "
            f"concordance={concordance_state}"
        ),
        event_metadata={
            "diagnosis": req.diagnosis.value,
            "certainty": req.certainty.value,
            "three_way_divergent": is_three_way_divergent,
            "concordance_state": concordance_state,
        },
        timestamp=datetime.utcnow(),
    ))

    db.flush()
    try:
        artifact = finalize_case_pdf(db, participant, visit, rec_c)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Reviewer C outcome was not finalized because SharePoint filing failed: {exc}")
    db.commit()
    return {
        "status": "success",
        "subject_id": subject_id,
        "concordance_status": concordance_state,
        "participant_status": participant.status.value if hasattr(participant.status, "value") else str(participant.status),
        "three_way_divergent": is_three_way_divergent,
        "message": "Reviewer C determination submitted successfully."
        ,"pdf_filed": True
        ,"pdf_sha256": artifact.pdf_sha256
    }


@router.post("/{subject_id}/lock")
def lock_committee_decision(subject_id: str, req: CommitteeLockRequest, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter(
        (Participant.subject_id == subject_id) |
        (Participant.case_number == subject_id)
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    if req.final_diagnosis == DiagnosisCode.OTHER:
        raise HTTPException(
            status_code=422,
            detail="Other may only be submitted through the Reviewer C escalation path with mandatory rationale.",
        )

    if not req.quorum_met or req.members_present < 3:
        raise HTTPException(
            status_code=400,
            detail="Quorum must be met (minimum 3 members present) to lock committee decision."
        )

    visit = db.query(AdjudicationVisit).filter_by(
        participant_id=participant.id, visit_number=req.visit_number
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="The subject visit does not exist.")
    decision = db.query(CommitteeDecision).filter_by(visit_id=visit.id).first()
    if decision and decision.locked:
        raise HTTPException(
            status_code=409,
            detail=f"Case {subject_id} already has a locked final decision and cannot be modified."
        )

    raw_sig = f"{subject_id}|{req.chair_upn}|{req.final_diagnosis.value}|{datetime.utcnow().isoformat()}"
    sig_hash = hashlib.sha256(raw_sig.encode()).hexdigest()

    if not decision:
        decision = CommitteeDecision(
            participant_id=participant.id, visit_id=visit.id,
            visit_number=req.visit_number, chair_rationale=req.chair_rationale,
        )
        db.add(decision)


    decision.adopted_reviewer = req.adopted_reviewer
    decision.final_diagnosis = req.final_diagnosis
    decision.date_of_diagnosis = req.date_of_diagnosis
    decision.final_onset_class = req.final_onset_class
    decision.final_severity = req.final_severity
    decision.final_certainty = req.final_certainty
    decision.chair_rationale = req.chair_rationale
    decision.quorum_met = req.quorum_met
    decision.members_present = req.members_present
    decision.chair_upn = req.chair_upn
    decision.chair_name = req.chair_name
    decision.signed_at = datetime.utcnow()
    decision.signature_hash = sig_hash
    decision.locked = True
    decision.locked_at = datetime.utcnow()
    decision.concordance_status = "CHAIR_LOCKED"

    participant.status = AdjudicationStatus.FINALIZED

    # Audit event for committee lock
    db.add(AuditEvent(
        event_type="COMMITTEE_DECISION_LOCKED",
        participant_id=participant.id,
        actor_upn=req.chair_upn,
        actor_role="CHAIR",
        description=(
            f"Committee locked final decision: {req.final_diagnosis.value} "
            f"(adopted {req.adopted_reviewer.value})"
        ),
        event_metadata={
            "final_diagnosis": req.final_diagnosis.value,
            "adopted_reviewer": req.adopted_reviewer.value,
            "chair_rationale": req.chair_rationale,
            "signature_hash": sig_hash,
        },
        timestamp=datetime.utcnow(),
    ))

    db.commit()

    return {
        "status": "success",
        "subject_id": subject_id,
        "final_diagnosis": req.final_diagnosis.value,
        "adopted_reviewer": req.adopted_reviewer.value if hasattr(req.adopted_reviewer, "value") else str(req.adopted_reviewer),
        "signature_hash": sig_hash,
        "locked_at": decision.locked_at.isoformat()
    }

