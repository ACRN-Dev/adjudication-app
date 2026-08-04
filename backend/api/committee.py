"""
Committee Review API — POST /api/committee/{subject_id}/lock
Chair consensus arbitration for discordant cases (OAC Charter §10).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import hashlib

from database import get_db
from models.canonical import Participant, CommitteeDecision, ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus

router = APIRouter()


class CommitteeLockRequest(BaseModel):
    adopted_reviewer: ReviewerRole
    final_diagnosis: DiagnosisCode
    final_onset_class: OnsetClass
    final_severity: SeverityGrade
    final_certainty: CertaintyLevel
    chair_rationale: str
    chair_upn: str
    chair_name: str
    quorum_met: bool = True
    members_present: int = 3


@router.post("/{subject_id}/lock")
def lock_committee_decision(subject_id: str, req: CommitteeLockRequest, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    raw_sig = f"{subject_id}|{req.chair_upn}|{req.final_diagnosis.value}|{datetime.utcnow().isoformat()}"
    sig_hash = hashlib.sha256(raw_sig.encode()).hexdigest()

    decision = CommitteeDecision(
        participant_id=participant.id,
        adopted_reviewer=req.adopted_reviewer,
        final_diagnosis=req.final_diagnosis,
        final_onset_class=req.final_onset_class,
        final_severity=req.final_severity,
        final_certainty=req.final_certainty,
        chair_rationale=req.chair_rationale,
        quorum_met=req.quorum_met,
        members_present=req.members_present,
        chair_upn=req.chair_upn,
        chair_name=req.chair_name,
        signed_at=datetime.utcnow(),
        signature_hash=sig_hash,
        locked=True,
        locked_at=datetime.utcnow()
    )

    participant.status = AdjudicationStatus.FINALIZED

    db.add(decision)
    db.commit()

    return {
        "status": "success",
        "subject_id": subject_id,
        "final_diagnosis": req.final_diagnosis.value,
        "signature_hash": sig_hash,
        "locked_at": decision.locked_at.isoformat()
    }
