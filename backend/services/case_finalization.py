"""Idempotent signed-case PDF generation and controlled filing."""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from models.canonical import AuditEvent, SignedCaseArtifact
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
    if existing and existing.filing_status == "FILED":
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
        "longitudinalComment": determination.longitudinal_comment or "",
        "firstPeVisitNumber": determination.first_pe_visit_number,
        "firstPeDate": determination.first_pe_date.isoformat() if determination.first_pe_date else "",
        "otherRationale": determination.other_rationale or "",
        "reviewerName": determination.reviewer_name or determination.reviewer_upn,
        "reviewerRole": determination.reviewer_role.value,
        "signedAt": determination.signed_at.isoformat(),
        "signatureHash": determination.signature_hash,
        "fullText": determination.comment or determination.rationale or "",
        "fetalNeonatalAssessments": getattr(determination, "fetal_neonatal_assessments", None) or getattr(visit, "final_fetal_assessments", None) or [],
        "gestationalAgeAtDelivery": getattr(determination, "gestational_age_at_delivery", None),
        "pregnancyOutcome": getattr(determination, "pregnancy_outcome", None),
    }
    pdf_bytes = generate_adjudication_pdf(case_data)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    artifact = existing or SignedCaseArtifact(
        participant_id=participant.id,
        visit_id=visit.id,
        determination_record_id=determination.id,
        pdf_sha256=digest,
        storage_provider="PENDING",
        storage_reference="UNFILED",
        filing_status="PENDING",
    )
    if existing and existing.pdf_sha256 != digest:
        artifact.filing_status = "FAILED_BLOCKED"
        artifact.filing_error = "Regenerated signed artifact does not match the immutable stored checksum"
        visit.filing_status = artifact.filing_status
        visit.filing_error = artifact.filing_error
        return artifact
    if not existing:
        db.add(artifact)
        db.flush()
    artifact.filing_attempts += 1
    try:
        adapter = get_etmf_adapter()
        destination = adapter.write(
            subject_id=participant.subject_id,
            blinded_id=case_reference,
            visit_code=visit.visit_code,
            study=participant.study.value,
            pdf_bytes=pdf_bytes,
            timestamp=determination.signed_at,
        )
        receipt = adapter.verify(destination, digest)
        artifact.storage_provider = adapter.__class__.__name__
        artifact.storage_reference = receipt.destination
        artifact.manifest_sha256 = receipt.manifest_sha256
        artifact.filing_verified_at = receipt.verified_at
        artifact.filing_receipt = {
            "receipt_id": receipt.receipt_id,
            "destination": receipt.destination,
            "content_sha256": receipt.content_sha256,
            "manifest_sha256": receipt.manifest_sha256,
            "verified_at": receipt.verified_at.isoformat(),
        }
        artifact.filing_status = "FILED"
        artifact.filed_at = receipt.verified_at
        artifact.filing_error = None
        visit.filing_status = "FILED"
        visit.filing_error = None
        db.add(AuditEvent(
            event_type="SIGNED_ARTIFACT_FILED",
            participant_id=participant.id,
            actor_upn="SYSTEM",
            actor_name="Qualified filing service",
            actor_role="SYSTEM",
            description=f"Signed artifact filed and checksum verified for visit {visit.visit_code}",
            event_metadata={
                "visit_id": str(visit.id), "artifact_id": str(artifact.id),
                "receipt_id": receipt.receipt_id, "pdf_sha256": digest,
                "storage_provider": artifact.storage_provider,
            },
            timestamp=datetime.utcnow(),
        ))
    except Exception as exc:
        # The signed determination remains durable. A monitor can retry filing
        # without asking the adjudicator to sign the clinical decision again.
        artifact.filing_status = "FAILED_RETRYABLE"
        artifact.filing_error = str(exc)[:1000]
        visit.filing_status = "FAILED_RETRYABLE"
        visit.filing_error = artifact.filing_error
        db.add(AuditEvent(
            event_type="SIGNED_ARTIFACT_FILING_FAILED",
            participant_id=participant.id,
            actor_upn="SYSTEM",
            actor_name="Qualified filing service",
            actor_role="SYSTEM",
            description=f"Signed artifact filing or verification failed for visit {visit.visit_code}",
            event_metadata={"visit_id": str(visit.id), "artifact_id": str(artifact.id), "error": artifact.filing_error},
            timestamp=datetime.utcnow(),
        ))
    return artifact
