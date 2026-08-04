"""
Reconciliation Engine API — POST /api/reconcile/{subject_id}
Compares EDC vs eSource values for a participant, generates discrepancy classifications.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.canonical import Participant, CanonicalField, DiscrepancyCategory
from services.resolve_value import resolve_value

router = APIRouter()


@router.post("/{subject_id}")
def reconcile_participant(subject_id: str, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    fields = participant.canonical_fields
    discrepancies = []
    for f in fields:
        if f.is_blinded:
            continue
        res = resolve_value(edc_value=f.edc_value, esource_value=f.esource_value)
        f.canonical_value = str(res.canonical_value) if res.canonical_value is not None else None
        f.discrepant = res.discrepant
        if res.discrepancy_category:
            f.discrepancy_category = res.discrepancy_category.value

        if res.discrepant:
            discrepancies.append({
                "canonical_field": f.canonical_field,
                "edc_value": f.edc_value,
                "esource_value": f.esource_value,
                "resolved_value": res.canonical_value,
                "category": res.discrepancy_category.value if res.discrepancy_category else "VALUE_DISCREPANCY",
                "clinically_meaningful": res.clinically_meaningful_discrepancy,
                "notes": res.notes
            })

    db.commit()

    return {
        "subject_id": subject_id,
        "total_fields": len(fields),
        "discrepancies_found": len(discrepancies),
        "discrepancies": discrepancies
    }
