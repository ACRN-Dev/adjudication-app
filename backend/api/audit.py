"""
Audit Trail API — GET /api/audit/{subject_id}
Immutable 21 CFR Part 11 event log query.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.canonical import AuditEvent, Participant

router = APIRouter()


@router.get("/{subject_id}")
def get_audit_trail(subject_id: str, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    events = db.query(AuditEvent).filter_by(participant_id=participant.id).order_by(AuditEvent.timestamp.asc()).all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "actor_name": e.actor_name,
            "actor_upn": e.actor_upn,
            "description": e.description,
            "previous_value": e.previous_value,
            "new_value": e.new_value,
            "record_hash": e.record_hash,
            "timestamp": e.timestamp.isoformat() if e.timestamp else ""
        }
        for e in events
    ]
