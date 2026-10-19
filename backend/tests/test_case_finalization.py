import uuid
from datetime import datetime
from pathlib import Path

from conftest import TestingSession
from models.canonical import (
    AdjudicationRecord, AdjudicationVisit, DiagnosisCode, Participant,
    ReviewerRole, SignedCaseArtifact, StudyCode,
)
from models.admin import AdjudicationActivityLedger
from services.case_finalization import finalize_case_pdf
from services.etmf_adapter import LocalFilesystemAdapter, get_etmf_adapter


def test_finalization_creates_exactly_one_pdf_artifact(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ETMF_ADAPTER", "local")
    output_root = Path(__file__).parent.parent / ".etmf_local" / "test-finalization"
    monkeypatch.setenv("ETMF_LOCAL_ROOT", str(output_root))
    db = TestingSession()
    try:
        suffix = uuid.uuid4().hex[:8]
        participant = Participant(
            subject_id=f"SUB-{suffix}", case_number=f"CASE-{suffix}", study=StudyCode.EOPE
        )
        db.add(participant)
        db.flush()
        visit = AdjudicationVisit(
            participant_id=participant.id, visit_number=1, visit_code="V01",
            visit_date=datetime(2026, 8, 20),
        )
        db.add(visit)
        db.flush()
        record = AdjudicationRecord(
            participant_id=participant.id, visit_id=visit.id, visit_number=1,
            reviewer_role=ReviewerRole.REVIEWER_B, reviewer_upn="b@example.test",
            reviewer_name="Reviewer B", diagnosis=DiagnosisCode.SEVERE_PE,
            comment="Screen determination comment.", signed=True,
            signed_at=datetime(2026, 8, 21, 9), signature_hash="a" * 64,
        )
        db.add(record)
        db.flush()

        first = finalize_case_pdf(db, participant, visit, record)
        from services.case_finalization import record_determination_activity
        ledger_row = record_determination_activity(db, participant, visit, record)
        second = finalize_case_pdf(db, participant, visit, record)
        db.commit()

        assert first.id == second.id
        assert db.query(SignedCaseArtifact).filter_by(visit_id=visit.id).count() == 1
        pdfs = list(output_root.rglob(f"*{participant.case_number}-V01.pdf"))
        assert len(pdfs) == 1
        assert pdfs[0].read_bytes().startswith(b"%PDF")
        assert first.storage_reference == str(pdfs[0])
        assert first.filing_status == "FILED"
        assert first.filing_verified_at is not None
        assert first.manifest_sha256 == first.pdf_sha256
        assert first.filing_receipt["content_sha256"] == first.pdf_sha256
        assert first.filing_receipt["receipt_id"]
        assert ledger_row.blinded_case_reference == f"{participant.case_number}-V01"
        assert participant.subject_id not in ledger_row.blinded_case_reference
    finally:
        db.close()


def test_finalization_fails_closed_when_destination_bytes_do_not_reconcile(monkeypatch, tmp_path):
    import services.case_finalization as finalization

    class TamperingAdapter(LocalFilesystemAdapter):
        def write(self, *args, **kwargs):
            destination = super().write(*args, **kwargs)
            Path(destination).write_bytes(b"tampered after upload")
            return destination

    monkeypatch.setattr(finalization, "get_etmf_adapter", lambda: TamperingAdapter(str(tmp_path)))
    db = TestingSession()
    try:
        suffix = uuid.uuid4().hex[:8]
        participant = Participant(subject_id=f"SUB-{suffix}", case_number=f"CASE-{suffix}", study=StudyCode.EOPE)
        db.add(participant)
        db.flush()
        visit = AdjudicationVisit(participant_id=participant.id, visit_number=1, visit_code="V01")
        db.add(visit)
        db.flush()
        record = AdjudicationRecord(
            participant_id=participant.id, visit_id=visit.id, visit_number=1,
            reviewer_role=ReviewerRole.REVIEWER_A, reviewer_upn="a@example.test",
            diagnosis=DiagnosisCode.PE, signed=True, signed_at=datetime(2026, 8, 21, 9),
            signature_hash="b" * 64,
        )
        db.add(record)
        db.flush()

        artifact = finalize_case_pdf(db, participant, visit, record)
        db.commit()

        assert artifact.filing_status == "FAILED_RETRYABLE"
        assert visit.filing_status == "FAILED_RETRYABLE"
        assert artifact.filing_verified_at is None
        assert artifact.filing_receipt is None
        assert "checksum reconciliation failed" in artifact.filing_error
        from models.canonical import AuditEvent
        assert db.query(AuditEvent).filter_by(
            participant_id=participant.id, event_type="SIGNED_ARTIFACT_FILING_FAILED"
        ).count() == 1
    finally:
        db.close()


def test_local_etmf_adapter_is_prohibited_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ETMF_ADAPTER", "local")
    try:
        get_etmf_adapter()
        assert False, "production must reject local eTMF filing"
    except RuntimeError as exc:
        assert "prohibited in production" in str(exc)
