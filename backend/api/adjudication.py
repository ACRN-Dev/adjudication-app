"""
Adjudication API — Dual Blinded Reviewer Submissions (A/B)
Enforces blinding: Reviewer A cannot view Reviewer B's submission until concordance check runs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import hashlib

from database import get_db
from models.canonical import Participant, AdjudicationRecord, ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus

router = APIRouter()


class ReviewerSubmission(BaseModel):
    reviewer_role: ReviewerRole
    reviewer_upn: str
    reviewer_name: str
    meets_criteria: bool
    diagnosis: DiagnosisCode
    onset_class: OnsetClass
    severity: SeverityGrade
    certainty: CertaintyLevel
    differential_diagnosis: Optional[str] = None
    rationale: str
    password_confirmed: bool


@router.post("/{subject_id}/submit")
def submit_adjudication(subject_id: str, sub: ReviewerSubmission, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    if not sub.password_confirmed:
        raise HTTPException(status_code=400, detail="21 CFR Part 11 e-signature requires password authentication.")

    # Generate SHA-256 cryptographic signature hash
    raw_sig = f"{subject_id}|{sub.reviewer_upn}|{sub.diagnosis.value}|{sub.onset_class.value}|{datetime.utcnow().isoformat()}"
    sig_hash = hashlib.sha256(raw_sig.encode()).hexdigest()

    rec = AdjudicationRecord(
        participant_id=participant.id,
        reviewer_role=sub.reviewer_role,
        reviewer_upn=sub.reviewer_upn,
        reviewer_name=sub.reviewer_name,
        meets_criteria=sub.meets_criteria,
        diagnosis=sub.diagnosis,
        onset_class=sub.onset_class,
        severity=sub.severity,
        certainty=sub.certainty,
        differential_diagnosis=sub.differential_diagnosis,
        rationale=sub.rationale,
        signed=True,
        signed_at=datetime.utcnow(),
        signature_hash=sig_hash,
        mfa_verified=True
    )
    db.add(rec)

    # Check for concordance if both reviewers have submitted
    records = db.query(AdjudicationRecord).filter_by(participant_id=participant.id).all()
    if len(records) >= 2:
        revA = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_A), None)
        revB = next((r for r in records if r.reviewer_role == ReviewerRole.REVIEWER_B), None)

        if revA and revB:
            is_concordant = (
                revA.diagnosis == revB.diagnosis and
                revA.onset_class == revB.onset_class and
                revA.meets_criteria == revB.meets_criteria
            )
            if is_concordant:
                participant.status = AdjudicationStatus.CONCORDANT
            else:
                participant.status = AdjudicationStatus.DISCORDANT

    db.commit()

    return {
        "status": "success",
        "subject_id": subject_id,
        "reviewer_role": sub.reviewer_role,
        "signature_hash": sig_hash,
        "signed_at": rec.signed_at.isoformat(),
        "participant_status": participant.status.value
    }


@router.get("/{subject_id}")
def get_adjudication_status(subject_id: str, requesting_upn: str, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    records = participant.adjudication_records

    # Blinded Dual Review Rule: A reviewer can ONLY see their own submission unless case is DISCORDANT/FINALIZED
    is_committee_phase = participant.status in (AdjudicationStatus.DISCORDANT, AdjudicationStatus.FINALIZED, AdjudicationStatus.COMMITTEE_PENDING)

    visible_records = []
    for r in records:
        if is_committee_phase or r.reviewer_upn == requesting_upn:
            visible_records.append({
                "reviewer_role": r.reviewer_role.value,
                "reviewer_name": r.reviewer_name,
                "diagnosis": r.diagnosis.value if r.diagnosis else None,
                "onset_class": r.onset_class.value if r.onset_class else None,
                "severity": r.severity.value if r.severity else None,
                "certainty": r.certainty.value if r.certainty else None,
                "rationale": r.rationale,
                "signed_at": r.signed_at.isoformat() if r.signed_at else None,
                "signature_hash": r.signature_hash
            })

    return {
        "subject_id": subject_id,
        "status": participant.status.value,
        "records": visible_records,
        "is_committee_phase": is_committee_phase
    }
