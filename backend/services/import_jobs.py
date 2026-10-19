"""Durable, leased import job dispatch and crash recovery."""
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta

from database import SessionLocal
from models.longitudinal import RTImportBatch, RTImportJob

LEASE_SECONDS = int(os.getenv("RT_IMPORT_JOB_LEASE_SECONDS", "900"))
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def enqueue_import_job(db, batch_id, reset=False):
    operation = "REPROCESS" if reset else "PROCESS"
    active = db.query(RTImportJob).filter(
        RTImportJob.batch_id == batch_id,
        RTImportJob.status.in_(["QUEUED", "RUNNING"]),
    ).first()
    if active:
        return active
    job = RTImportJob(batch_id=batch_id, operation=operation, status="QUEUED")
    db.add(job)
    db.flush()
    return job


def claim_job(db, job_id, worker_id=WORKER_ID, now=None):
    now = now or datetime.utcnow()
    lease_until = now + timedelta(seconds=LEASE_SECONDS)
    updated = db.query(RTImportJob).filter(
        RTImportJob.id == job_id,
        RTImportJob.attempts < RTImportJob.max_attempts,
        (RTImportJob.status == "QUEUED")
        | ((RTImportJob.status == "RUNNING") & (RTImportJob.lease_expires_at < now)),
    ).update({
        RTImportJob.status: "RUNNING",
        RTImportJob.lease_owner: worker_id,
        RTImportJob.lease_expires_at: lease_until,
        RTImportJob.last_heartbeat_at: now,
        RTImportJob.started_at: now,
        RTImportJob.attempts: RTImportJob.attempts + 1,
    }, synchronize_session=False)
    db.commit()
    return updated == 1


def execute_import_job(job_id):
    db = SessionLocal()
    try:
        if not claim_job(db, job_id):
            return False
        job = db.get(RTImportJob, job_id)
        batch_id, reset = job.batch_id, job.operation == "REPROCESS"
    finally:
        db.close()

    # Import locally to keep the pipeline independent of job orchestration.
    from services.realtime_pipeline import process_batch
    heartbeat_stop = threading.Event()

    def heartbeat():
        interval = max(5, LEASE_SECONDS // 3)
        while not heartbeat_stop.wait(interval):
            heartbeat_db = SessionLocal()
            try:
                now = datetime.utcnow()
                heartbeat_db.query(RTImportJob).filter_by(
                    id=job_id, status="RUNNING", lease_owner=WORKER_ID
                ).update({
                    RTImportJob.last_heartbeat_at: now,
                    RTImportJob.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS),
                }, synchronize_session=False)
                heartbeat_db.commit()
            finally:
                heartbeat_db.close()

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        process_batch(batch_id, reset=reset)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1)

    db = SessionLocal()
    retry = False
    try:
        job = db.get(RTImportJob, job_id)
        batch = db.get(RTImportBatch, job.batch_id) if job else None
        if not job or job.lease_owner != WORKER_ID:
            return False
        succeeded = bool(batch and batch.status in {"AUTO_QC_COMPLETE", "MONITOR_QC_REQUIRED", "PUBLISHED"})
        job.status = "SUCCEEDED" if succeeded else ("QUEUED" if job.attempts < job.max_attempts else "FAILED")
        retry = job.status == "QUEUED"
        job.error_summary = None if succeeded else ((batch.error_summary if batch else None) or "Import did not reach a completed state")
        job.finished_at = datetime.utcnow() if job.status in {"SUCCEEDED", "FAILED"} else None
        job.lease_owner = None; job.lease_expires_at = None
        db.commit()
    finally:
        db.close()
    return execute_import_job(job_id) if retry else succeeded


def dispatch_pending_jobs():
    """Recover committed queued jobs and jobs abandoned after lease expiry."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        ids = [row[0] for row in db.query(RTImportJob.id).filter(
            (RTImportJob.status == "QUEUED")
            | ((RTImportJob.status == "RUNNING") & (RTImportJob.lease_expires_at < now))
        ).all()]
    finally:
        db.close()
    for job_id in ids:
        threading.Thread(target=execute_import_job, args=(job_id,), daemon=True).start()
