import uuid
from datetime import datetime, timedelta

from models.longitudinal import LongitudinalAuditEvent, RTImportBatch, RTImportJob
from services.import_jobs import claim_job, enqueue_import_job
from services.realtime_pipeline import audit, verify_audit_chain


def _batch(db_session):
    batch = RTImportBatch(
        filename="durable.csv", checksum=uuid.uuid4().hex + uuid.uuid4().hex,
        file_size=10, uploaded_by="monitor@example.org", source_path="pending.csv",
    )
    db_session.add(batch); db_session.flush()
    return batch


def test_import_job_is_committed_state_and_only_one_worker_claims(db_session):
    batch = _batch(db_session)
    job = enqueue_import_job(db_session, batch.id)
    db_session.commit()

    assert db_session.get(RTImportJob, job.id).status == "QUEUED"
    assert claim_job(db_session, job.id, worker_id="worker-a") is True
    assert claim_job(db_session, job.id, worker_id="worker-b") is False


def test_expired_import_job_lease_can_be_recovered(db_session):
    batch = _batch(db_session)
    job = enqueue_import_job(db_session, batch.id)
    db_session.commit()
    assert claim_job(db_session, job.id, worker_id="dead-worker") is True
    job = db_session.get(RTImportJob, job.id)
    job.lease_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    assert claim_job(db_session, job.id, worker_id="recovery-worker") is True
    assert db_session.get(RTImportJob, job.id).attempts == 2


def test_audit_chain_detects_tampering(db_session):
    audit(db_session, "actor", "ROLE", "ONE", "CASE", "1", {"value": 1})
    audit(db_session, "actor", "ROLE", "TWO", "CASE", "1", {"value": 2})
    db_session.commit()
    assert verify_audit_chain(db_session) is True

    first = db_session.query(LongitudinalAuditEvent).order_by(LongitudinalAuditEvent.chain_sequence).first()
    first.safe_details = {"value": 999, "outcome": "SUCCESS"}
    db_session.commit()
    assert verify_audit_chain(db_session) is False
