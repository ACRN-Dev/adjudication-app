"""
Data Import API — POST /api/import/edc and /api/import/esource
Accepts CSV uploads, validates columns, creates ImportBatch + CanonicalFields.
"""

import io, hashlib, csv
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.canonical import ImportBatch, Participant, CanonicalField, StudyCode, SourceSystem
from services.resolve_value import resolve_value

router = APIRouter()


# ── Required EDC columns (canonical names after mapping) ──────────────────
EDC_REQUIRED_COLS = {"SUBJID", "SiteName", "GA_EVENT", "SBP", "DBP", "EVENT_DT"}
ESOURCE_REQUIRED_COLS = {"SUBJID", "VITAL_SBP", "VITAL_DBP", "VITAL_DT"}

# ── Blinding guardrail — these column names MUST NEVER enter canonical fields
BLINDED_KEYWORDS = {
    "sflt", "plgf", "seng", "flt1", "ratio", "poc_result",
    "biomarker", "sFlt-1", "PlGF"
}


def _check_blinding(columns: list[str]) -> list[str]:
    """Return any column names that violate blinding rules."""
    violations = []
    for col in columns:
        if any(kw.lower() in col.lower() for kw in BLINDED_KEYWORDS):
            violations.append(col)
    return violations


def _parse_csv(content: bytes) -> tuple[list[str], list[dict]]:
    """Parse CSV bytes → (headers, rows as list of dicts)."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = list(reader)
    return list(headers), rows


class ImportResponse(BaseModel):
    batch_id: str
    study: str
    participants_imported: int
    validation_errors: list
    blinding_violations: list
    status: str
    message: str


@router.post("/edc", response_model=ImportResponse)
async def import_edc(
    file: UploadFile = File(...),
    study: str = Form(...),
    mapping_version: str = Form(default="1.0"),
    imported_by: str = Form(default="system"),
    db: Session = Depends(get_db),
):
    """
    Import an EDC CSV export.
    Validates columns, enforces blinding guardrail, creates ImportBatch.
    """
    content = await file.read()
    headers, rows = _parse_csv(content)

    # Blinding check (SOP-ADJ-002)
    violations = _check_blinding(headers)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=f"SOP-ADJ-002 VIOLATION: Blinded columns detected in EDC file: {violations}. "
                   f"File rejected. Remove biomarker columns before import."
        )

    # Column validation
    missing_cols = EDC_REQUIRED_COLS - set(headers)
    validation_errors = [f"Missing required column: {col}" for col in missing_cols]

    # Create import batch
    batch = ImportBatch(
        study=StudyCode(study),
        edc_filename=file.filename,
        edc_export_date=datetime.utcnow(),
        edc_row_count=len(rows),
        mapping_version=mapping_version,
        imported_by=imported_by,
        validation_errors=validation_errors,
        status="COMPLETE" if not validation_errors else "PARTIAL",
    )
    db.add(batch)
    db.flush()

    participants_imported = 0
    for row in rows:
        subj_id = row.get("SUBJID", "").strip()
        if not subj_id:
            continue

        # Create or retrieve participant
        participant = db.query(Participant).filter_by(
            subject_id=subj_id, study=StudyCode(study)
        ).first()

        if not participant:
            participant = Participant(
                subject_id=subj_id,
                case_number=row.get("CaseNo", ""),
                site_code=row.get("SiteCode", ""),
                site_name=row.get("SiteName", ""),
                study=StudyCode(study),
                import_batch_id=batch.id,
                trigger_code=row.get("TriggerCode", ""),
            )
            db.add(participant)
            db.flush()
            participants_imported += 1

        # Store canonical fields from EDC
        for col, val in row.items():
            if col in ("SUBJID", "SiteName", "SiteCode", "CaseNo"):
                continue
            if any(kw.lower() in col.lower() for kw in BLINDED_KEYWORDS):
                continue  # Double-check — skip blinded fields

            field = CanonicalField(
                participant_id=participant.id,
                import_batch_id=batch.id,
                mapping_version=mapping_version,
                canonical_field=col,
                edc_value=str(val) if val else None,
                source_used=SourceSystem.EDC,
            )
            db.add(field)

    db.commit()

    return ImportResponse(
        batch_id=str(batch.id),
        study=study,
        participants_imported=participants_imported,
        validation_errors=validation_errors,
        blinding_violations=violations,
        status=batch.status,
        message=f"EDC import complete. {participants_imported} participants, "
                f"{len(validation_errors)} validation errors.",
    )


@router.post("/esource", response_model=ImportResponse)
async def import_esource(
    file: UploadFile = File(...),
    study: str = Form(...),
    mapping_version: str = Form(default="1.0"),
    imported_by: str = Form(default="system"),
    db: Session = Depends(get_db),
):
    """
    Import an eSource CSV export and reconcile with existing EDC canonical fields.
    eSource NEVER overwrites EDC values — it fills gaps and flags discrepancies.
    """
    content = await file.read()
    headers, rows = _parse_csv(content)

    violations = _check_blinding(headers)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=f"SOP-ADJ-002 VIOLATION: Blinded columns in eSource file: {violations}."
        )

    missing_cols = ESOURCE_REQUIRED_COLS - set(headers)
    validation_errors = [f"Missing required column: {col}" for col in missing_cols]

    batch = ImportBatch(
        study=StudyCode(study),
        esource_filename=file.filename,
        esource_export_date=datetime.utcnow(),
        esource_row_count=len(rows),
        mapping_version=mapping_version,
        imported_by=imported_by,
        validation_errors=validation_errors,
        status="COMPLETE" if not validation_errors else "PARTIAL",
    )
    db.add(batch)
    db.flush()

    participants_processed = 0
    for row in rows:
        subj_id = row.get("SUBJID", "").strip()
        if not subj_id:
            continue

        participant = db.query(Participant).filter_by(
            subject_id=subj_id, study=StudyCode(study)
        ).first()

        if not participant:
            validation_errors.append(f"eSource row for {subj_id} has no matching EDC participant.")
            continue

        participants_processed += 1

        # Reconcile eSource fields against existing EDC canonical fields
        for col, esource_val in row.items():
            if col == "SUBJID":
                continue
            if any(kw.lower() in col.lower() for kw in BLINDED_KEYWORDS):
                continue

            # Find existing EDC canonical field for this participant
            existing = db.query(CanonicalField).filter_by(
                participant_id=participant.id,
                canonical_field=col,
            ).first()

            edc_val = existing.edc_value if existing else None
            resolved = resolve_value(edc_value=edc_val, esource_value=esource_val or None)

            if existing:
                existing.esource_value = resolved.esource_value
                existing.discrepant = resolved.discrepant
                if resolved.discrepancy_category:
                    existing.discrepancy_category = resolved.discrepancy_category.value
            else:
                # EDC absent — eSource fills gap
                field = CanonicalField(
                    participant_id=participant.id,
                    import_batch_id=batch.id,
                    mapping_version=mapping_version,
                    canonical_field=col,
                    esource_value=str(esource_val) if esource_val else None,
                    canonical_value=str(resolved.canonical_value) if resolved.canonical_value else None,
                    source_used=SourceSystem.ESOURCE,
                    discrepant=resolved.discrepant,
                )
                db.add(field)

    db.commit()

    return ImportResponse(
        batch_id=str(batch.id),
        study=study,
        participants_imported=participants_processed,
        validation_errors=validation_errors,
        blinding_violations=violations,
        status=batch.status,
        message=f"eSource reconciliation complete. {participants_processed} participants processed.",
    )


@router.get("/batches")
def list_import_batches(db: Session = Depends(get_db)):
    batches = db.query(ImportBatch).order_by(ImportBatch.import_timestamp.desc()).all()
    return [
        {
            "id": str(b.id),
            "study": b.study,
            "edc_filename": b.edc_filename,
            "esource_filename": b.esource_filename,
            "mapping_version": b.mapping_version,
            "import_timestamp": b.import_timestamp.isoformat() if b.import_timestamp else None,
            "status": b.status,
            "participant_count": len(b.participants),
        }
        for b in batches
    ]
