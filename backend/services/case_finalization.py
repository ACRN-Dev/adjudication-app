"""Idempotent signed-case PDF generation and controlled filing."""
import hashlib

from sqlalchemy.orm import Session

from models.canonical import SignedCaseArtifact
from models.admin import AdjudicationActivityLedger
from services.etmf_adapter import get_etmf_adapter
from services.pdf_generator import generate_adjudication_pdf


def record_determination_activity(db, participant, visit, determination):
    """Append one idempotent billable activity fact for a signed visit decision."""
    key = f"DETERMINATION_SIGNED:{determination.id}"
    row = db.query(AdjudicationActivityLedger).filter_by(idempotency_key=key).first()
    if row:
        return row
    row = AdjudicationActivityLedger(
        adjudicator_upn=determination.reviewer_upn.strip().lower(),
        study_code=participant.study.value if hasattr(participant.study, "value") else str(participant.study),
        blinded_case_reference=f"{participant.case_number or f'CASE-{participant.id}'}-{visit.visit_code}",
        subject_visit_id=str(visit.id),
        role_served=determination.reviewer_role.value,
        event_type="DETERMINATION_SIGNED",
        event_at=determination.signed_at,
        billable=True,
        source_record_id=str(determination.id),
        idempotency_key=key,
        metadata_json={"visit_code": visit.visit_code, "visit_number": visit.visit_number},
    )
    db.add(row)
    return row


def finalize_case_pdf(db: Session, participant, visit, determination) -> SignedCaseArtifact:
    existing = db.query(SignedCaseArtifact).filter_by(visit_id=visit.id).first()
    if existing:
        return existing

    case_reference = participant.case_number or f"CASE-{participant.id}"
    case_data = {
        "id": case_reference,
        "caseNo": case_reference,
        "site": "[Blinded per SOP-ADJ-002]",
        "visitNumber": visit.visit_number,
        "visitCode": visit.visit_code,
        "visitDate": visit.visit_date.isoformat() if visit.visit_date else "Not supplied",
        "finalDiagnosis": determination.diagnosis.value,
        "derivedSubtype": determination.onset_class.value if determination.onset_class else "Not classified",
        "derivedSeverity": determination.severity.value if determination.severity else "Not classified",
        "certainty": determination.certainty.value if determination.certainty else "Not classified",
        "comment": determination.comment or determination.rationale or "",
        "otherRationale": determination.other_rationale or "",
        "reviewerName": determination.reviewer_name or determination.reviewer_upn,
        "reviewerRole": determination.reviewer_role.value,
        "signedAt": determination.signed_at.isoformat(),
        "signatureHash": determination.signature_hash,
        "fullText": determination.comment or determination.rationale or "",
    }
    pdf_bytes = generate_adjudication_pdf(case_data)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    artifact = SignedCaseArtifact(
        participant_id=participant.id,
        visit_id=visit.id,
        determination_record_id=determination.id,
        pdf_sha256=digest,
        # Older local SQLite demo databases created these fields as NOT NULL.
        # Keep neutral placeholders until the eTMF adapter confirms filing; the
        # explicit filing_status remains the source of truth for filed vs retry.
        storage_provider="PENDING",
        storage_reference="UNFILED",
        filed_at=determination.signed_at,
        filing_status="PENDING",
    )
    db.add(artifact)
    db.flush()
    adapter = get_etmf_adapter()
    artifact.filing_attempts += 1
    try:
        destination = adapter.write(
            subject_id=participant.subject_id,
            blinded_id=f"{case_reference}-{visit.visit_code}",
            study=participant.study.value,
            pdf_bytes=pdf_bytes,
            timestamp=determination.signed_at,
        )
        artifact.storage_provider = adapter.__class__.__name__
        artifact.storage_reference = destination
        artifact.filing_status = "FILED"
        artifact.filed_at = determination.signed_at
        visit.filing_status = "FILED"
        visit.filing_error = None
    except Exception as exc:
        # The signed determination remains durable. A monitor can retry filing
        # without asking the adjudicator to sign the clinical decision again.
        artifact.filing_status = "FAILED_RETRYABLE"
        artifact.filing_error = str(exc)[:1000]
        visit.filing_status = "FAILED_RETRYABLE"
        visit.filing_error = artifact.filing_error
    return artifact
