"""Secure RealTime import, Monitor database, and assigned-case API."""
import hashlib, json, os, re, uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter,UploadFile,File,BackgroundTasks,Depends,HTTPException,Header,Query,Request,Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session,selectinload
from database import get_db
from models.longitudinal import RTImportBatch,LongitudinalParticipant,VisitInstance,VisitDerivation,ImportIssue,ReviewerAssignment,ReviewerRecusal,ClinicalDataQuery,ObservationCorrection,LongitudinalCaseDerivation,LabReferenceRange,CanonicalObservation,RestrictedIdentityCrosswalk
from models.history import PatientHistoryField, PatientRiskSummary, PatientHistory
from services.realtime_pipeline import checksum_file,audit
from services.import_jobs import enqueue_import_job, execute_import_job
from services.auth_service import current_user, audit_auth
from services.lab_reference import evaluate_participant_labs, LAB_ANALYTES
from services.import_readiness import participant_import_readiness
from services.realtime_mapping import parse_datetime
from services.realtime_mapping import parse_numeric, parse_coded
from services.longitudinal_derivation import derive_participant
from models.auth import PortalUser
from models.admin import AdjudicatorStudyContract
from models.canonical import AdjudicationRecord, AdjudicationVisit, Participant
from services.clinical_derivation import RULE_VERSION
router = APIRouter()
MONITOR = {"ADJUDICATION_COORDINATOR", "MONITOR_QC_REVIEWER", "QA_REVIEWER", "RELEASE_OPERATOR", "MONITOR", "ADMIN", "MEDICAL_OFFICER", "MEDICAL_MONITOR"}
MEDICAL_OFFICER = "MEDICAL_OFFICER"
ADJUDICATOR_ROLES = {"ADJUDICATOR", "REVIEWER_A", "REVIEWER_B", "REVIEWER_C"}
COMPLETED_VISIT_STATUSES = {"COMPLETED", "FINALIZED", "LOCKED", "CLOSED", "CONCORDANT", "DISCORDANT", "THREE_WAY_DIVERGENT", "RESOLVED_BY_MAJORITY"}


def _demo_contract_bypass_enabled() -> bool:
    """Demo data and demo-account deployments may assign without contract fixtures."""
    return any(
        os.getenv(flag, "false").strip().lower() == "true"
        for flag in ("ENABLE_DEMO_DATA", "ENABLE_DEMO_ACCOUNTS")
    )

def actor(request: Request, x_demo_user: str | None = Header(None), x_demo_role: str | None = Header(None), db: Session = Depends(get_db)):
    token = request.cookies.get("acrn_demo_session")
    if token:
        from services.auth_service import resolve_session
        from services.monitor_security import ROLES as MONITOR_PORTAL_ROLES
        s = resolve_session(db, token)
        if s is None:
            # Cookie present but no matching session — likely the container restarted
            # and the SQLite/Postgres session table was reset, or the token was revoked.
            raise HTTPException(
                401,
                detail={"message": "Session not found. Please sign in again.", "reason": "session_not_found"},
            )
        if s.expires_at <= datetime.utcnow():
            raise HTTPException(
                401,
                detail={"message": "Your session has expired. Please sign in again.", "reason": "session_expired"},
            )
        u = db.get(PortalUser, s.user_id)
        if u is None or u.status != "ACTIVE":
            raise HTTPException(
                401,
                detail={"message": "Account not found or inactive. Contact your administrator.", "reason": "account_inactive"},
            )
        if u.must_change_password:
            raise HTTPException(403, detail={"code": "PASSWORD_CHANGE_REQUIRED", "message": "You must set a new password before continuing."})
        if u.role in {"MONITOR", "MEDICAL_OFFICER", "MEDICAL_MONITOR"}:
            pr = u.portal_role
            if not pr or pr not in MONITOR_PORTAL_ROLES:
                return u.email, "MONITOR", False, _study_scope(u.study_scope)
            return u.email, pr, True, _study_scope(u.study_scope)
        if u.role in {"ADMIN", "OWNER"}:
            return u.email, u.role, True, _study_scope(u.study_scope)
        if u.role in {"ADJUDICATOR", "CHAIRPERSON"}:
            return u.email, u.role, False, _study_scope(u.study_scope)
        raise HTTPException(403, f"Monitor/QC authority required. Current role: {u.role}")
    # No cookie at all — fall back to demo headers only when demo mode is enabled,
    # and only after verifying the claimed user actually exists with that role.
    # Trusting the header value alone would let anyone impersonate any adjudicator.
    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true":
        if x_demo_user and x_demo_role:
            claimed_email = x_demo_user.strip().lower()
            claimed_role = x_demo_role.strip().upper()
            demo_user = db.query(PortalUser).filter_by(email=claimed_email, status="ACTIVE").first()
            # Fixed demo identities may be used before demo fixtures are seeded;
            # arbitrary headers are never accepted.
            known_demo = {
                "monitor.demo@acrnhealth.com": "MONITOR",
                "monitor1@acrnhealth.com": "MONITOR_QC_REVIEWER",
                "monitor2@acrnhealth.com": "QA_REVIEWER",
                "adjudicatora@acrnhealth.com": "ADJUDICATOR",
                "adjudicatorb@acrnhealth.com": "ADJUDICATOR",
                "adjudicatorc@acrnhealth.com": "ADJUDICATOR",
            }
            if not demo_user and known_demo.get(claimed_email) == claimed_role:
                return claimed_email, claimed_role, claimed_role in MONITOR, {"*"}
            if not demo_user or not demo_user.is_demo_account:
                raise HTTPException(401, detail={"message": "Unrecognized demo identity.", "reason": "no_session"})
            if demo_user.must_change_password:
                raise HTTPException(403, detail={"code": "PASSWORD_CHANGE_REQUIRED", "message": "You must set a new password before continuing."})
            allowed_claimed_roles = {demo_user.role}
            if demo_user.role in {"MONITOR", "MEDICAL_OFFICER", "MEDICAL_MONITOR"} and demo_user.portal_role:
                allowed_claimed_roles.add(demo_user.portal_role)
            if demo_user.role == "ADJUDICATOR":
                allowed_claimed_roles.update({"REVIEWER_A", "REVIEWER_B", "REVIEWER_C"})
            if claimed_role not in allowed_claimed_roles:
                raise HTTPException(403, detail={"message": "Role mismatch for demo identity.", "reason": "role_mismatch"})
            is_qc = claimed_role in MONITOR or demo_user.role in {"MONITOR", "MEDICAL_OFFICER", "MEDICAL_MONITOR", "ADMIN", "OWNER"}
            return demo_user.email, claimed_role, is_qc, _study_scope(demo_user.study_scope)
    raise HTTPException(401, detail={"message": "Authentication required. Please sign in.", "reason": "no_session"})


def _study_scope(value: str | None) -> set[str]:
    studies = {item.strip() for item in (value or "*").split(",") if item.strip()}
    return studies or {"*"}


def _identity_studies(identity) -> set[str]:
    # Direct service-level tests and internal callers created before scoped identities
    # use the original three-field tuple. Treat those trusted calls as wildcard-scoped;
    # every HTTP identity produced by actor() carries an explicit fourth field.
    return identity[3] if len(identity) > 3 else {"*"}


def _scope_participant_query(query, identity):
    studies = _identity_studies(identity)
    return query if "*" in studies else query.filter(LongitudinalParticipant.study.in_(studies))


def _require_participant_scope(participant: LongitudinalParticipant, identity) -> None:
    studies = _identity_studies(identity)
    if "*" not in studies and participant.study not in studies:
        # Do not reveal that an out-of-scope participant exists.
        raise HTTPException(404, "Participant not found")


def monitor(i = Depends(actor)):
    if not i[2]:
        raise HTTPException(403, "Monitor/QC authority required — portal role not provisioned. Contact your administrator.")
    return i


def is_medical_officer(i) -> bool:
    return i[1] == MEDICAL_OFFICER


def require_qc_monitor(i):
    if is_medical_officer(i):
        raise HTTPException(403, "Medical Officer access is limited to case data, data queries, and completeness status.")
    return i


def adjudicator(i = Depends(actor)):
    if i[1] not in ADJUDICATOR_ROLES:
        raise HTTPException(403, "Adjudicator role required")
    return i


# Coarse, monotonically increasing progress estimate for the async batch pipeline.
# FAILED/CANCELLED map to 0, not 100 — a failed batch never actually completed, and
# showing a full bar next to a FAILED badge previously read as a false success signal.
_STAGE_PCT = {
    "UPLOADED": 5, "CHECKSUM_CALCULATED": 10, "STRUCTURE_VALIDATION": 20, "ROWS_STAGED": 30,
    "VISITS_RECONSTRUCTED": 85, "AUTO_QC_COMPLETE": 100, "MONITOR_QC_REQUIRED": 100, "FAILED": 0, "CANCELLED": 0,
}


def _progress_pct(b):
    base = _STAGE_PCT.get(b.status, 0)
    if b.status == "ROWS_STAGED" and b.row_count:
        # Interpolate within the row-processing stage using rows_processed/row_count.
        frac = min(1.0, (b.rows_processed or 0) / max(1, b.row_count))
        return int(30 + frac * 55)
    return base


def bjson(b, db=None):
    report = {"accepted": 0, "accepted_with_warnings": 0, "rejected": 0, "participants": []}
    if db and b.status in {"AUTO_QC_COMPLETE", "MONITOR_QC_REQUIRED"}:
        participants = db.query(LongitudinalParticipant).filter_by(source_batch_id=b.id).all()
        for participant in participants:
            readiness = participant_import_readiness(participant)
            if readiness["status"] == "ACCEPTED":
                report["accepted"] += 1
            elif readiness["status"] == "ACCEPTED_WITH_WARNINGS":
                report["accepted_with_warnings"] += 1
            else:
                report["rejected"] += 1
            report["participants"].append({"subject_id": participant.blinded_subject_id, **readiness})
    return {"id":str(b.id),"filename":b.filename,"checksum":b.checksum,"file_size":b.file_size,"uploaded_at":b.uploaded_at,"rows":b.row_count,"rows_processed":b.rows_processed,"participants":b.participant_count,"visits":b.visit_count,"mapping_version":b.mapping_version,"status":b.status,"progress_pct":_progress_pct(b),"validation_result":b.validation_result,"blinding_result":b.blinding_result,"errors":b.error_count,"warnings":b.warning_count,"prohibited_excluded":b.prohibited_count,"finished_at":b.processing_finished_at,"error_summary":b.error_summary,"import_report":report}
@router.post("/batches",status_code=202)
async def upload(background:BackgroundTasks,file:UploadFile=File(...),i=Depends(monitor),db:Session=Depends(get_db)):
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(415,"RealTime import requires CSV")
    staging=os.path.join(os.path.dirname(os.path.dirname(__file__)),".rt-staging"); os.makedirs(staging,exist_ok=True)
    path=os.path.join(staging,f"{uuid.uuid4()}.csv"); size=0
    with open(path,"wb") as out:
        while chunk:=await file.read(1024*1024): size+=len(chunk); out.write(chunk)
    checksum=checksum_file(path); existing=db.query(RTImportBatch).filter_by(checksum=checksum).first()
    if existing: os.remove(path); raise HTTPException(409,{"message":"Exact duplicate file","batch_id":str(existing.id)})
    b=RTImportBatch(filename=os.path.basename(file.filename),checksum=checksum,file_size=size,uploaded_by=i[0],source_path=path,status="CHECKSUM_CALCULATED")
    db.add(b); db.flush(); audit(db,i[0],i[1],"BATCH_UPLOADED","IMPORT_BATCH",b.id,{"filename":b.filename,"size":size,"checksum":checksum}); job=enqueue_import_job(db,b.id); db.commit(); background.add_task(execute_import_job,job.id); return bjson(b, db)
@router.post("/batches/bulk",status_code=202)
async def upload_bulk(background:BackgroundTasks,files:list[UploadFile]=File(...),i=Depends(monitor),db:Session=Depends(get_db)):
    """Accept multiple RealTime CSV snapshots in one request; each is queued and processed independently
    so a single malformed file does not block the rest of the batch of files."""
    results=[]
    staging=os.path.join(os.path.dirname(os.path.dirname(__file__)),".rt-staging"); os.makedirs(staging,exist_ok=True)
    for file in files:
        entry={"filename":file.filename}
        try:
            if not (file.filename or "").lower().endswith(".csv"):
                entry.update(status="REJECTED",error="RealTime import requires CSV"); results.append(entry); continue
            path=os.path.join(staging,f"{uuid.uuid4()}.csv"); size=0
            with open(path,"wb") as out:
                while chunk:=await file.read(1024*1024): size+=len(chunk); out.write(chunk)
            checksum=checksum_file(path); existing=db.query(RTImportBatch).filter_by(checksum=checksum).first()
            if existing:
                os.remove(path); entry.update(status="DUPLICATE",batch_id=str(existing.id)); results.append(entry); continue
            b=RTImportBatch(filename=os.path.basename(file.filename),checksum=checksum,file_size=size,uploaded_by=i[0],source_path=path,status="CHECKSUM_CALCULATED")
            db.add(b); db.flush(); audit(db,i[0],i[1],"BATCH_UPLOADED","IMPORT_BATCH",b.id,{"filename":b.filename,"size":size,"checksum":checksum,"bulk":True}); job=enqueue_import_job(db,b.id); db.commit()
            background.add_task(execute_import_job,job.id)
            entry.update(status="QUEUED",batch=bjson(b, db)); results.append(entry)
        except Exception as exc:
            db.rollback(); entry.update(status="ERROR",error=str(exc)); results.append(entry)
    return {"total":len(files),"accepted":sum(1 for r in results if r["status"]=="QUEUED"),"items":results}
@router.get("/batches")
def batches(i=Depends(monitor),db:Session=Depends(get_db)): return [bjson(x, db) for x in db.query(RTImportBatch).order_by(RTImportBatch.uploaded_at.desc()).all()]
@router.get("/batches/{batch_id}")
def batch(batch_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    b=db.get(RTImportBatch,batch_id)
    if not b: raise HTTPException(404,"Batch not found")
    return bjson(b, db)
@router.post("/batches/{batch_id}/cancel")
def cancel(batch_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    b=db.get(RTImportBatch,batch_id)
    if not b or b.status in {"PUBLISHED","SUPERSEDED"}: raise HTTPException(409,"Batch cannot be cancelled")
    b.cancel_requested=True; audit(db,i[0],i[1],"IMPORT_CANCEL_REQUESTED","IMPORT_BATCH",b.id); db.commit(); return {"status":"CANCEL_REQUESTED"}
@router.post("/batches/{batch_id}/reprocess")
@router.post("/batches/{batch_id}/retry")
def reprocess_batch_endpoint(batch_id:uuid.UUID,background:BackgroundTasks,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    b=db.get(RTImportBatch,batch_id)
    if not b: raise HTTPException(404,"Batch not found")
    if b.status in {"PUBLISHED","SUPERSEDED"}: raise HTTPException(409,"Published or superseded batch cannot be reprocessed")
    if not b.source_path or not os.path.exists(b.source_path):
        raise HTTPException(400,"Source file no longer available on staging")
    b.status="CHECKSUM_CALCULATED"
    b.error_count=0
    b.error_summary=None
    b.cancel_requested=False
    audit(db,i[0],i[1],"BATCH_REPROCESS_REQUESTED","IMPORT_BATCH",b.id)
    job=enqueue_import_job(db,b.id,reset=True)
    db.commit()
    background.add_task(execute_import_job,job.id)
    return {"status":"QUEUED","batch":bjson(b)}
@router.delete("/batches/{batch_id}")
def delete_batch(batch_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    """Demo-only: remove one batch and everything it staged, so a corrected file can be
    re-uploaded cleanly. Gated to demo/offline environments — production import history
    must never be silently deleted."""
    from services.demo_reset_service import is_demo_environment
    if not is_demo_environment():
        raise HTTPException(409,"Deleting import batches is disabled outside demo/offline environments.")
    b=db.get(RTImportBatch,batch_id)
    if not b: raise HTTPException(404,"Batch not found")
    db.query(CanonicalObservation).filter_by(source_batch_id=b.id).delete()
    db.query(VisitInstance).filter_by(source_batch_id=b.id).delete()
    db.query(PatientHistoryField).filter_by(source_batch_id=b.id).delete()
    p_ids=[p[0] for p in db.query(LongitudinalParticipant.id).filter_by(source_batch_id=b.id).all()]
    if p_ids:
        db.query(RestrictedIdentityCrosswalk).filter(RestrictedIdentityCrosswalk.participant_id.in_(p_ids)).delete(synchronize_session=False)
        db.query(PatientRiskSummary).filter(PatientRiskSummary.participant_id.in_(p_ids)).delete(synchronize_session=False)
        db.query(PatientHistory).filter(PatientHistory.participant_id.in_(p_ids)).delete(synchronize_session=False)
        db.query(LongitudinalCaseDerivation).filter(LongitudinalCaseDerivation.participant_id.in_(p_ids)).delete(synchronize_session=False)
        db.query(LongitudinalParticipant).filter(LongitudinalParticipant.id.in_(p_ids)).delete(synchronize_session=False)
    db.query(ImportIssue).filter_by(batch_id=b.id).delete()
    staging_path=b.source_path
    audit(db,i[0],i[1],"IMPORT_BATCH_DELETED","IMPORT_BATCH",b.id,{"filename":b.filename,"status":b.status})
    db.delete(b); db.commit()
    if staging_path and os.path.exists(staging_path):
        try: os.remove(staging_path)
        except OSError: pass
    return {"status":"DELETED"}
@router.post("/batches/reset-demo")
def reset_realtime_batches(i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    """Demo-only: wipe every RealTime batch and its derived longitudinal data so the
    Imports page can start completely fresh. Never touches canonical adjudication
    records, users, or admin fixtures."""
    from services.demo_reset_service import is_demo_environment, purge_realtime_batches
    if not is_demo_environment():
        raise HTTPException(409,"Resetting RealTime imports is disabled outside demo/offline environments.")
    counts=purge_realtime_batches(db)
    audit(db,i[0],i[1],"REALTIME_IMPORTS_RESET","IMPORT_BATCH","ALL",{"deleted":counts})
    db.commit()
    return {"status":"RESET_COMPLETE","deleted":counts}
def completion_state(db, p):
    """Project canonical adjudication completion onto every RealTime snapshot row."""
    canonical = db.query(Participant).filter(
        (Participant.subject_id == p.blinded_subject_id)
        | (Participant.case_number == p.blinded_subject_id)
    ).first()
    if not canonical:
        return False, 0
    visits = db.query(AdjudicationVisit).filter_by(participant_id=canonical.id).all()
    completed = bool(visits) and all(
        (visit.status or "").upper() in COMPLETED_VISIT_STATUSES for visit in visits
    )
    return completed, len(visits)


ADJUDICATOR_CAPACITY_LIMIT = 6


def active_assignment_workloads(db, exclude_participant_id=None):
    """Return active workload counts, excluding canonical completed cases."""
    workloads = {}
    assignments = db.query(ReviewerAssignment).filter_by(status="ASSIGNED").all()
    for assignment in assignments:
        if exclude_participant_id is not None and assignment.participant_id == exclude_participant_id:
            continue
        participant = assignment.participant
        if participant is not None and completion_state(db, participant)[0]:
            continue
        reviewer_upn = (assignment.reviewer_upn or "").strip().lower()
        workloads[reviewer_upn] = workloads.get(reviewer_upn, 0) + 1
    return workloads


def pjson(p, db=None, include_assignments=True):
    assignments = []
    try:
        if hasattr(p, "reviewer_assignments") and p.reviewer_assignments:
            assignments = [{"reviewer_upn": a.reviewer_upn, "reviewer_role": a.reviewer_role} for a in p.reviewer_assignments]
    except Exception:
        assignments = []
    is_completed, canonical_visit_count = completion_state(db, p) if db else (False, 0)
    readiness = participant_import_readiness(p)
    age_val = None
    if db:
        f = (
            db.query(PatientHistoryField)
            .filter(
                PatientHistoryField.participant_id == p.id,
                PatientHistoryField.field_key.in_(["age", "age_years", "age_at_enrollment"])
            )
            .first()
        )
        if f and f.value:
            try: age_val = int(f.value)
            except: age_val = f.value
            
    def _get_recon(p, db):
        if not db or not p.source_batch_id: return {}
        b = db.get(RTImportBatch, p.source_batch_id)
        if not b or not b.validation_result: return {}
        res = b.validation_result
        if isinstance(res, str):
            import json
            try: res = json.loads(res)
            except: res = {}
        return (res or {}).get("reconciliation", {})

    payload = {
        "id":str(p.id),
        "subject_id":p.blinded_subject_id,
        "age": age_val,
        "study":p.study,
        "visit_count":p.available_visit_count or 0,
        "first_visit":p.first_visit_date.isoformat() if p.first_visit_date else None,
        "latest_visit":p.latest_visit_date.isoformat() if p.latest_visit_date else None,
        "pregnancy_status":p.pregnancy_status,
        "derived_onset":p.derived_onset_date.isoformat() if p.derived_onset_date else None,
        "onset_classification":p.derived_onset_classification,
        "maximum_severity":p.maximum_severity,
        "packet_completeness":p.packet_completeness or 0.0,
        "history_completeness": getattr(p, "history_completeness", 0.0),
        "open_issues":p.open_data_issues or 0,
        "qc_status":p.workflow_status,
        "source_batch_id":str(p.source_batch_id) if p.source_batch_id else None,
        "is_completed": is_completed,
        "case_status": "COMPLETED" if is_completed else p.workflow_status,
        "canonical_visit_count": canonical_visit_count,
        "import_readiness": readiness,
        "reconciliation": _get_recon(p, db),
    }
    if include_assignments:
        payload["assignments"] = assignments
    return payload


def medical_pjson(p, db):
    payload = pjson(p, db, include_assignments=False)
    return {
        "id": payload["id"],
        "subject_id": payload["subject_id"],
        "age": payload["age"],
        "study": payload["study"],
        "visit_count": payload["visit_count"],
        "first_visit": payload["first_visit"],
        "latest_visit": payload["latest_visit"],
        "pregnancy_status": payload["pregnancy_status"],
        "packet_completeness": payload["packet_completeness"],
        "history_completeness": payload["history_completeness"],
        "open_issues": payload["open_issues"],
        "import_readiness": payload["import_readiness"],
    }


def medical_timeline(p, db):
    payload = timeline(p, db, include_assignments=False)
    safe_visits = []
    for visit in payload.get("visits", []):
        interpretation = visit.get("interpretation", {})
        safe_visits.append({
            "id": visit["id"],
            "name": visit["name"],
            "visit_number": visit["visit_number"],
            "occurrence": visit["occurrence"],
            "date": visit["date"],
            "form": visit["form"],
            "form_version": visit["form_version"],
            "not_performed_reason": visit["not_performed_reason"],
            "evidence": visit["evidence"],
            "completeness": interpretation.get("completeness"),
            "missing": interpretation.get("missing", []),
        })
    return {
        **medical_pjson(p, db),
        "visits": safe_visits,
        "history": payload.get("history", {}),
        "risk_summary": payload.get("risk_summary", {}),
    }


@router.get("/patients")
def patients(page:int=1,page_size:int=100,search:str="",qc_status:str="",view:str="all",include_rejected:bool=False,i=Depends(monitor),db:Session=Depends(get_db)):
    page_val = int(page.default if hasattr(page, 'default') else page)
    size_val = int(page_size.default if hasattr(page_size, 'default') else page_size)
    q=_scope_participant_query(db.query(LongitudinalParticipant), i)
    if search:q=q.filter(LongitudinalParticipant.blinded_subject_id.ilike(f"%{search}%"))
    if qc_status:q=q.filter_by(workflow_status=qc_status)
    all_rows=q.order_by(LongitudinalParticipant.blinded_subject_id, LongitudinalParticipant.created_at.desc()).all()
    # A new source snapshot creates a new audit row, but it must not create a second
    # assignment target. Keep the newest snapshot for each blinded subject.
    latest_by_subject={}
    history_by_subject={}
    for row in all_rows:
        latest_by_subject.setdefault(row.blinded_subject_id, row)
        history_by_subject.setdefault(row.blinded_subject_id, []).append(row)
    projected=[]
    for row in latest_by_subject.values():
        payload=medical_pjson(row, db) if is_medical_officer(i) else pjson(row, db)
        if not include_rejected and not payload["import_readiness"]["accepted"]:
            continue
        historical_assignments=[]
        seen_assignments=set()
        for snapshot in history_by_subject.get(row.blinded_subject_id, []):
            for assignment in snapshot.reviewer_assignments or []:
                key=(assignment.reviewer_upn, assignment.reviewer_role)
                if key not in seen_assignments:
                    seen_assignments.add(key)
                    historical_assignments.append({"reviewer_upn": assignment.reviewer_upn, "reviewer_role": assignment.reviewer_role})
        if historical_assignments and not is_medical_officer(i):
            payload["assignments"] = historical_assignments
        if view.lower() == "completed" and not payload["is_completed"]: continue
        if view.lower() == "active" and payload["is_completed"]: continue
        projected.append((row, payload))
    projected.sort(key=lambda pair: pair[1]["subject_id"])
    total=len(projected)
    items=projected[(page_val-1)*size_val:page_val*size_val]
    return {"page":page_val,"page_size":size_val,"total":total,"view":view,"items":[{**payload,"lab_issues":evaluate_participant_labs(db,row)} for row,payload in items]}
def loaded(db,pid): return db.query(LongitudinalParticipant).options(selectinload(LongitudinalParticipant.visits).selectinload(VisitInstance.observations),selectinload(LongitudinalParticipant.reviewer_assignments)).filter_by(id=pid).first()
def history_item(f):
    return {
        "domain": f.domain,
        "field_key": f.field_key,
        "key": f.field_key,
        "field_label_raw": f.field_label_raw,
        "label": f.field_label_raw,
        "field_type": f.field_type,
        "value": f.value,
        "value_precision": f.value_precision,
        "precision": f.value_precision,
        "instance_index": f.instance_index,
        "instance": f.instance_index,
        "signed_at": f.signed_at.isoformat() if f.signed_at else None,
        "amber_flag": f.amber_flag,
        "flag_reason": f.flag_reason,
    }


def _timeline_visit_number(visit, fallback):
    match = re.search(r"(?:^|\b)V(?:ISIT)?\s*0?([1-9]\d*)\b", str(visit.scheduled_visit_code or ""), re.IGNORECASE)
    return int(match.group(1)) if match else fallback


def _embedded_source_datetime(value):
    """Parse plain or serialized RealTime date values without mutating source data."""
    parsed = parse_datetime(str(value or ""))
    if parsed:
        return parsed
    for candidate in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', str(value or "")):
        parsed = parse_datetime(candidate.replace('\\"', '"').strip())
        if parsed:
            return parsed
    return None


def _participant_approved_edd(participant):
    """Return one consistent source EDD, or no anchor when source EDDs conflict."""
    dated = []
    for visit in participant.visits:
        for observation in visit.observations:
            if observation.superseded:
                continue
            if str(observation.canonical_variable or "").lower() != "edd":
                continue
            parsed = (
                observation.datetime_value
                or _embedded_source_datetime(observation.raw_source_value)
                or _embedded_source_datetime(observation.parsed_text_value)
            )
            if parsed:
                dated.append(parsed.date())
    unique = sorted(set(dated))
    return (unique[0], unique) if len(unique) == 1 else (None, unique)


def _resolved_visit_ga(visit, resolved_date, approved_edd, conflicting_edds=None):
    """Resolve GA per visit; never borrow a gestational age from another visit."""
    code = str(visit.scheduled_visit_code or "").upper()
    if code == "V06":
        return None, "POSTPARTUM", None

    source_days = visit.gestational_age_days if visit.gestational_age_days and visit.gestational_age_days >= 45 else None
    derived_days = None
    if approved_edd and resolved_date:
        derived_days = 280 - (approved_edd - resolved_date.date()).days
        if not 45 <= derived_days <= 315:
            derived_days = None

    discrepancy = None
    if conflicting_edds:
        discrepancy = {
            "is_conflicting": True,
            "type": "CONFLICTING_DATING_ANCHORS",
            "message": "Multiple source EDD values prevent deterministic gestational-age calculation.",
            "source_edds": [value.isoformat() for value in conflicting_edds],
        }
    elif source_days is not None and derived_days is not None and abs(source_days - derived_days) > 1:
        discrepancy = {
            "is_conflicting": True,
            "type": "SOURCE_VS_DERIVED_GA",
            "message": (
                f"Source GA {source_days // 7}w{source_days % 7}d conflicts with "
                f"EDD-derived GA {derived_days // 7}w{derived_days % 7}d."
            ),
            "source_ga_days": source_days,
            "derived_ga_days": derived_days,
        }

    if source_days is not None:
        return source_days, "SOURCE_RECORDED", discrepancy
    if derived_days is not None:
        return derived_days, "DERIVED_FROM_APPROVED_EDD", discrepancy
    return None, "UNAVAILABLE", discrepancy


def timeline(p,db, reviewer_upn=None, include_assignments=True):
    canonical_participant = db.query(Participant).filter(
        (Participant.case_number == p.blinded_subject_id)
        | (Participant.subject_id == p.blinded_subject_id)
    ).first()
    canonical_visits = {}
    reviewer_records = {}
    if canonical_participant:
        canonical_visits = {
            visit.visit_number: visit
            for visit in db.query(AdjudicationVisit).filter_by(participant_id=canonical_participant.id).all()
        }
        if reviewer_upn:
            reviewer_records = {
                record.visit_number: record
                for record in db.query(AdjudicationRecord).filter(
                    AdjudicationRecord.participant_id == canonical_participant.id,
                    AdjudicationRecord.reviewer_upn == reviewer_upn.strip().lower(),
                    AdjudicationRecord.signed.is_(True),
                ).all()
            }
    visits=[]
    persisted_derivations = db.query(VisitDerivation).filter_by(participant_id=p.id).all()
    derivations_by_visit = {}
    for derivation in persisted_derivations:
        derivations_by_visit.setdefault(derivation.visit_id, {})[derivation.dv_identifier] = derivation
    approved_edd, source_edds = _participant_approved_edd(p)
    ordered_visits = sorted(
        [visit for visit in p.visits if re.fullmatch(r"V0[1-6]", str(visit.scheduled_visit_code or ""), re.IGNORECASE)],
        key=lambda x:(x.visit_sequence or 99, x.visit_datetime is None, x.visit_datetime or datetime.max),
    )
    for visit_index, v in enumerate(ordered_visits, start=1):
        visit_number = _timeline_visit_number(v, visit_index)
        evidence={}
        for o in v.observations:
            if o.prohibited_flag or o.superseded or o.canonical_variable.startswith("RECORDED_PE_"): continue
            evidence.setdefault(o.canonical_variable,[]).append({
                "value": o.numeric_value if o.numeric_value is not None else o.raw_source_value or o.parsed_text_value or o.coded_value,
                "numeric_value": o.numeric_value,
                "raw_source_value": o.raw_source_value,
                "parsed_text_value": o.parsed_text_value,
                "coded_value": o.coded_value,
                "unit": o.unit,
                "observed_at": o.observation_datetime,
                "date_confidence": o.date_confidence,
                "provenance": o.provenance_type,
                "observation_id": str(o.id),
                "supersedes_observation_id": str(o.supersedes_observation_id) if o.supersedes_observation_id else None,
                "source": {"form": o.source_form, "page": o.source_page, "field": o.source_field_label, "row": o.source_row_number},
            })
        canonical_visit = canonical_visits.get(visit_number)
        reviewer_record = reviewer_records.get(visit_number)
        obs_dts = [o.observation_datetime for o in v.observations if not o.superseded and o.observation_datetime]
        resolved_date = v.visit_datetime or (min(obs_dts) if obs_dts else None)
        resolved_ga_days, ga_provenance, ga_discrepancy = _resolved_visit_ga(
            v,
            resolved_date,
            approved_edd,
            source_edds if len(source_edds) > 1 else None,
        )
        ga_label = (
            f"{resolved_ga_days // 7} weeks, {resolved_ga_days % 7} days"
            if resolved_ga_days and resolved_ga_days >= 45
            else None
        )

        not_performed_reason = None
        for o in v.observations:
            if o.superseded: continue
            fld = (o.source_field_label or "").lower()
            val = str(o.raw_source_value or o.parsed_text_value or "").strip()
            if "not performing" in fld or "not performed" in fld or "missed" in fld or val.lower() in {"delivered", "missed visit", "withdrew", "lost to follow-up"}:
                not_performed_reason = val
                break

        visit_derivations = derivations_by_visit.get(v.id, {})
        versions = {item.rule_version for item in visit_derivations.values()}
        authoritative = bool(visit_derivations) and versions == {RULE_VERSION}
        dv_results = {key: item.result for key, item in visit_derivations.items()} if authoritative else {}
        completeness = dv_results.get("DV-26", {}).get("inputs", {}).get("score")
        interpretation = {
            "authoritative": authoritative,
            "engine_version": RULE_VERSION if authoritative else None,
            "derived_at": max((item.derived_at for item in visit_derivations.values()), default=None),
            "completeness": round(completeness * 100) if completeness is not None else None,
            "missing": dv_results.get("DV-26", {}).get("inputs", {}).get("missing", []),
            "certainty_gate": dv_results.get("DV-27") if authoritative else None,
            "trigger": dv_results.get("DV-30") if authoritative else None,
            "dv_results": dv_results,
            "failure_reason": None if authoritative else "Authoritative server derivation unavailable or rule versions do not match",
        }
        visits.append({
            "id":str(v.id),"name":v.scheduled_visit_code,"visit_number":visit_number,"occurrence":v.visit_occurrence,
            "date":resolved_date,"ga_days":resolved_ga_days,"source_ga_days":v.gestational_age_days,
            "ga":ga_label,"gestationalLabel":ga_label,"ga_provenance":ga_provenance,
            "ga_discrepancy":ga_discrepancy,"approved_edd":approved_edd.isoformat() if approved_edd else None,
            "form":v.form_title,
            "form_version":v.form_version,
            "not_performed_reason": not_performed_reason,
            "reconstruction":{"method":v.reconstruction_method,"confidence":v.reconstruction_confidence,"qc_status":v.qc_status},
            "evidence":evidence,
            "reconciliation":{
                "displayed_clinical_results": sum(len(items or []) for items in evidence.values()),
                "mapped_clinical_rows": sum(1 for o in v.observations if not o.prohibited_flag and not o.superseded and o.canonical_variable),
                "prohibited_blinded_rows": sum(1 for o in v.observations if o.prohibited_flag),
                "conflicting_rows": sum(1 for o in v.observations if not o.superseded and (o.quality_status or "").upper() == "CONFLICTING"),
            },
            "interpretation": interpretation,
            "signed": bool(reviewer_record),
            "status": canonical_visit.status if canonical_visit else None,
            "resolution_status": canonical_visit.status if canonical_visit else None,
            "finalized": bool(canonical_visit and (canonical_visit.finalized_at or canonical_visit.final_record_id)),
            "filing_status": canonical_visit.filing_status if canonical_visit else None,
            "signature": None if not reviewer_record else {
                "signer": reviewer_record.reviewer_name,
                "email": reviewer_record.reviewer_upn,
                "timestamp": reviewer_record.signed_at,
                "hash": reviewer_record.signature_hash,
                "visit_number": reviewer_record.visit_number,
            },
        })
    d=db.query(LongitudinalCaseDerivation).filter_by(participant_id=p.id).first()
    long=None if not d else {"earliest_qualifying_date":d.earliest_qualifying_pe_date,"first_qualifying_visit_id":str(d.first_qualifying_visit_id) if d.first_qualifying_visit_id else None,"onset_classification":d.onset_classification,"maximum_severity":d.maximum_severity,"packet_completeness":d.packet_completeness,"certainty_restriction":d.certainty_restriction,"trigger_status":d.trigger_status,"recorded_site_diagnosis":d.recorded_site_diagnosis,"recorded_site_diagnosis_date":d.recorded_site_diagnosis_date,"discrepancy":d.recorded_versus_derived_discrepancy,"explanation":d.explanation}
    history_fields = db.query(PatientHistoryField).filter_by(participant_id=p.id).order_by(PatientHistoryField.domain, PatientHistoryField.instance_index, PatientHistoryField.field_key).all()
    history = {"obstetric": [], "conditions": [], "medications": [], "medical": [], "family": [], "allergy_surgery": [], "baseline": []}
    age_from_fields = None
    for f in history_fields:
        item = history_item(f)
        if f.field_key == "age" and f.value:
            age_from_fields = f.value
        if f.domain in history:
            history[f.domain].append(item)
        if f.domain == "conditions":
            history["medical"].append(item)
        elif f.domain in {"medical", "family", "allergy_surgery"}:
            history["conditions"].append(item)
    rs = db.query(PatientRiskSummary).filter_by(participant_id=p.id).first()
    parsed_age = int(age_from_fields) if (age_from_fields and str(age_from_fields).isdigit()) else age_from_fields
    risk_summary = {"age": parsed_age, "chips": rs.chips if rs else [], "parity_summary": rs.parity_summary if rs else "", "gravidity": rs.gravidity if rs else 0, "parity": rs.parity if rs else 0, "miscarriages": rs.miscarriages if rs else 0, "stillbirths": rs.stillbirths if rs else 0, "vaginal_deliveries": rs.vaginal_deliveries if rs else 0, "c_sections": rs.c_sections if rs else 0, "chronic_htn": rs.chronic_htn if rs else False, "pregestational_diabetes": rs.pregestational_diabetes if rs else False}
    return {**pjson(p, db, include_assignments=include_assignments),"age":parsed_age,"visits":visits,"longitudinal":long,"history":history,"risk_summary":risk_summary}
@router.get("/patients/{participant_id}")
def patient(participant_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    p=loaded(db,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    _require_participant_scope(p, i)
    audit(db,i[0],i[1],"PATIENT_DATA_ACCESSED","PARTICIPANT",p.id,{"portal":"MONITOR","role":i[1]}); db.commit()
    if is_medical_officer(i):
        return {**medical_timeline(p, db), "lab_issues": evaluate_participant_labs(db, p)}
    return {**timeline(p,db,i[0]),"lab_issues":evaluate_participant_labs(db,p)}
class MonitorApprovalRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/patients/{participant_id}/approve")
def approve(participant_id:uuid.UUID, req: MonitorApprovalRequest | None = Body(default=None), i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    p=db.get(LongitudinalParticipant,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    _require_participant_scope(p, i)
    approved_edd, source_edds = _participant_approved_edd(p)
    if len(source_edds) > 1:
        raise HTTPException(409,"Monitor/QC review is required to resolve conflicting source EDDs.")
    for visit in p.visits:
        observation_dates = [o.observation_datetime for o in visit.observations if o.observation_datetime]
        resolved_date = visit.visit_datetime or (min(observation_dates) if observation_dates else None)
        _, _, discrepancy = _resolved_visit_ga(visit, resolved_date, approved_edd)
        if discrepancy:
            raise HTTPException(409,"Monitor/QC review is required to resolve conflicting gestational-age evidence.")
    readiness = participant_import_readiness(p)
    if readiness["status"] == "REJECTED":
        raise HTTPException(409, {"message": "Hard import-readiness rejection cannot be overridden.", "readiness": readiness})
    if readiness["status"] == "ACCEPTED_WITH_WARNINGS" and not ((req.reason if req else None) or "").strip():
        raise HTTPException(422, {"message": "A Monitor reason is required to approve with warnings.", "readiness": readiness})
    if db.query(ImportIssue).filter_by(participant_id=p.id,resolution_status="OPEN").filter(ImportIssue.severity.in_(["ERROR", "CRITICAL"])).count(): raise HTTPException(409,"Unresolved critical import issues block approval")
    p.workflow_status="QC_APPROVED"
    audit(db,i[0],i[1],"PARTICIPANT_MONITOR_APPROVED","PARTICIPANT",p.id,{
        "original_readiness_status": readiness["status"],
        "warnings": readiness.get("warnings", []),
        "monitor_reason": (req.reason if req else None),
        "approved_at": datetime.utcnow().isoformat(),
    })
    db.commit(); return {"status":p.workflow_status,"readiness":readiness}
@router.post("/patients/{participant_id}/assign")
def assign(participant_id:uuid.UUID,reviewer_upn:str,reviewer_role:str,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    p=db.get(LongitudinalParticipant,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    _require_participant_scope(p, i)
    if completion_state(db, p)[0]: raise HTTPException(409,"This case is already completed and cannot be assigned")
    readiness = participant_import_readiness(p)
    if readiness["status"] == "REJECTED":
        raise HTTPException(409, {"message": "Hard import-readiness rejection cannot be assigned.", "readiness": readiness})
    if p.workflow_status=="MONITOR_QC_REQUIRED" and readiness["status"] == "ACCEPTED":
        p.workflow_status="QC_APPROVED"
    elif p.workflow_status=="MONITOR_QC_REQUIRED":
        raise HTTPException(409, {"message": "Monitor warning acknowledgement is required before assignment.", "readiness": readiness})
    if reviewer_role not in {"REVIEWER_A","REVIEWER_B"}: raise HTTPException(422,"Invalid reviewer role")
    reviewer_upn=reviewer_upn.strip().lower()
    reviewer=db.query(PortalUser).filter_by(email=reviewer_upn,role="ADJUDICATOR",status="ACTIVE").first()
    if not reviewer: raise HTTPException(422,f"Reviewer '{reviewer_upn}' must be an active adjudicator account")

    max_cases = ADJUDICATOR_CAPACITY_LIMIT
    active_cases = active_assignment_workloads(db, exclude_participant_id=p.id).get(reviewer_upn, 0)
    if active_cases >= max_cases:
        raise HTTPException(409, f"Reviewer capacity reached: {reviewer_upn} already has {active_cases}/{max_cases} active assignments. Rebalance the roster before assigning another case.")

    demo_contract_bypass = _demo_contract_bypass_enabled()
    if not demo_contract_bypass:
        now=datetime.utcnow()
        contract=db.query(AdjudicatorStudyContract).filter(
            AdjudicatorStudyContract.adjudicator_upn==reviewer_upn,
            AdjudicatorStudyContract.study_code==p.study,
            AdjudicatorStudyContract.status=="ACTIVE",
            AdjudicatorStudyContract.effective_from<=now,
            (AdjudicatorStudyContract.effective_to.is_(None)|(AdjudicatorStudyContract.effective_to>now)),
        ).first()
        if not contract: raise HTTPException(409,"Reviewer has no active contract for this study")
    existing=db.query(ReviewerAssignment).filter_by(participant_id=p.id,reviewer_role=reviewer_role).first()
    if existing: existing.reviewer_upn=reviewer_upn
    else: db.add(ReviewerAssignment(participant_id=p.id,reviewer_upn=reviewer_upn,reviewer_role=reviewer_role))
    p.workflow_status="ASSIGNED"; audit(db,i[0],i[1],"REVIEWER_ASSIGNED","PARTICIPANT",p.id,{"reviewer_role":reviewer_role,"reviewer_upn":reviewer_upn,"contract_verification":"BYPASSED_DEMO" if demo_contract_bypass else "VERIFIED"}); db.commit(); return {"status":"ASSIGNED","contract_verification":"BYPASSED_DEMO" if demo_contract_bypass else "VERIFIED"}
@router.get("/assigned")
def assigned(i=Depends(adjudicator),db:Session=Depends(get_db)):
    query=db.query(ReviewerAssignment,LongitudinalParticipant).join(LongitudinalParticipant,ReviewerAssignment.participant_id==LongitudinalParticipant.id).filter(ReviewerAssignment.reviewer_upn==i[0],LongitudinalParticipant.workflow_status=="ASSIGNED")
    studies = _identity_studies(i)
    if "*" not in studies:
        query=query.filter(LongitudinalParticipant.study.in_(studies))
    rows=query.all()
    return [pjson(p, db, include_assignments=False) for _,p in rows if not completion_state(db, p)[0]]

@router.get("/progress")
def progress(i=Depends(actor), db:Session=Depends(get_db)):
    """Return case-level resolution progress and identity-scoped reviewer signature progress."""
    if is_medical_officer(i):
        raise HTTPException(403, "Medical Officer access is limited to case data, data queries, and completeness status.")
    query = db.query(LongitudinalParticipant)
    if i[2]:
        query = _scope_participant_query(query, i)
    elif i[1] in ADJUDICATOR_ROLES:
        assigned_ids = [row.participant_id for row in db.query(ReviewerAssignment).filter_by(
            reviewer_upn=i[0], status="ASSIGNED"
        ).all()]
        query = query.filter(LongitudinalParticipant.id.in_(assigned_ids)) if assigned_ids else query.filter(False)
        query = _scope_participant_query(query, i)
    else:
        raise HTTPException(403, "Monitor/QC or adjudicator role required")

    rows = query.order_by(LongitudinalParticipant.blinded_subject_id, LongitudinalParticipant.created_at).all()
    grouped = {}
    for row in rows:
        grouped.setdefault(row.blinded_subject_id, []).append(row)

    adjudicated_statuses = {"COMPLETED", "FINALIZED", "LOCKED", "CLOSED", "CONCORDANT", "RESOLVED_BY_MAJORITY"}
    items = []
    total_visits = 0
    completed_visits = 0
    duplicate_source_records = 0
    reviewer_progress = {
        "signed_visits": 0,
        "pending_visits": 0,
        "completed_cases": 0,
        "in_progress_cases": 0,
        "pending_cases": 0,
    }
    for subject_id, participants in grouped.items():
        canonical = db.query(Participant).filter(
            (Participant.subject_id == subject_id) | (Participant.case_number == subject_id)
        ).first()
        visit_rows = []
        if canonical:
            canonical_visits = db.query(AdjudicationVisit).filter_by(participant_id=canonical.id).order_by(AdjudicationVisit.visit_number).all()
            for visit in canonical_visits:
                status = (visit.status or "PENDING").upper()
                visit_rows.append({"visit_number": visit.visit_number, "visit_code": visit.visit_code, "status": status})
        if not visit_rows:
            seen_visits = set()
            for participant in participants:
                for visit in sorted(participant.visits, key=lambda value: (value.visit_sequence or 999, value.visit_datetime or datetime.max)):
                    key = (visit.visit_sequence or 0, visit.scheduled_visit_code or visit.form_title)
                    if key in seen_visits:
                        continue
                    seen_visits.add(key)
                    visit_rows.append({
                        "visit_number": visit.visit_sequence or len(seen_visits),
                        "visit_code": visit.scheduled_visit_code or visit.form_title,
                        "status": "PENDING",
                    })
        case_completed = sum(1 for visit in visit_rows if visit["status"] in adjudicated_statuses)
        participant_ids = [participant.id for participant in participants]
        assigned_roles = {
            assignment.reviewer_role
            for assignment in db.query(ReviewerAssignment).filter(
                ReviewerAssignment.participant_id.in_(participant_ids),
                ReviewerAssignment.status == "ASSIGNED",
            ).all()
            if assignment.reviewer_upn.strip().lower() == i[0].strip().lower()
        }
        reviewer_signed_visits = set()
        if canonical and assigned_roles:
            reviewer_signed_visits = {
                record.visit_number
                for record in db.query(AdjudicationRecord).filter(
                    AdjudicationRecord.participant_id == canonical.id,
                    AdjudicationRecord.signed.is_(True),
                ).all()
                if record.reviewer_role.value in assigned_roles
                and record.reviewer_upn.strip().lower() == i[0].strip().lower()
            }
        my_signed_count = sum(
            1 for visit in visit_rows
            if visit["visit_number"] in reviewer_signed_visits
        )
        my_total_visits = len(visit_rows)
        my_status = (
            "COMPLETED" if my_total_visits and my_signed_count == my_total_visits else
            "IN_PROGRESS" if my_signed_count else
            "PENDING"
        )
        total_visits += len(visit_rows)
        completed_visits += case_completed
        duplicate_source_records += max(0, len(participants) - 1)
        case_status = "ADJUDICATED_CLOSED" if visit_rows and case_completed == len(visit_rows) else (
            "IN_PROGRESS" if case_completed else "PENDING"
        )
        reviewer_progress["signed_visits"] += my_signed_count
        reviewer_progress["pending_visits"] += my_total_visits - my_signed_count
        reviewer_progress[{
            "COMPLETED": "completed_cases",
            "IN_PROGRESS": "in_progress_cases",
            "PENDING": "pending_cases",
        }[my_status]] += 1
        assignments = db.query(ReviewerAssignment).filter(
            ReviewerAssignment.participant_id.in_(participant_ids)
        ).all()
        items.append({
            "subject_id": subject_id,
            "case_number": canonical.case_number if canonical else None,
            "status": case_status,
            "reviewer_status": my_status,
            "reviewer_signed_visits": my_signed_count,
            "reviewer_pending_visits": my_total_visits - my_signed_count,
            "total_visits": len(visit_rows),
            "completed_visits": case_completed,
            "pending_visits": len(visit_rows) - case_completed,
            "completion_pct": round(case_completed / len(visit_rows) * 100, 1) if visit_rows else 0,
            "visit_statuses": visit_rows,
            "source_batches": sorted({str(participant.source_batch_id) for participant in participants}),
            "duplicate_source_count": max(0, len(participants) - 1),
            "adjudicators": (
                sorted({assignment.reviewer_upn for assignment in assignments if assignment.reviewer_upn})
                if i[2]
                else ([i[0]] if assigned_roles else [])
            ),
        })

    unique_cases = len(items)
    by_case_status = {
        status: sum(1 for item in items if item["status"] == status)
        for status in ("PENDING", "IN_PROGRESS", "ADJUDICATED_CLOSED")
    }
    return {
        "items": items,
        "summary": {
            "unique_cases": unique_cases,
            "total_visits": total_visits,
            "adjudicated_visits": completed_visits,
            "pending_visits": total_visits - completed_visits,
            "completed_cases": sum(1 for item in items if item["status"] == "ADJUDICATED_CLOSED"),
            "completion_pct": round(completed_visits / total_visits * 100, 1) if total_visits else 0,
            "duplicate_source_records": duplicate_source_records,
            "reviewer_progress": {
                **reviewer_progress,
                "completion_pct": round(
                    reviewer_progress["signed_visits"]
                    / (reviewer_progress["signed_visits"] + reviewer_progress["pending_visits"])
                    * 100,
                    1,
                ) if reviewer_progress["signed_visits"] + reviewer_progress["pending_visits"] else 0,
            },
        },
        "by_case_status": by_case_status,
    }

@router.get("/adjudicators")
def adjudicators(i=Depends(monitor), db:Session=Depends(get_db)):
    require_qc_monitor(i)
    """Active roster; A/B are positional slots, never fixed identities."""
    rows = db.query(PortalUser).filter_by(role="ADJUDICATOR", status="ACTIVE").order_by(PortalUser.display_name).all()
    workloads = active_assignment_workloads(db)
    return [{"email": u.email, "display_name": u.display_name, "portal_role": u.portal_role,
             "active_workload": workloads.get(u.email.strip().lower(),0)} for u in rows]
_CLINICIAN_BIAS_FIELDS = {
    "pe_status",
    "recorded_pe_status",
    "recorded_pe_diagnosis",
    "clinician_diagnosis",
    "clinician_opinion",
    "site_diagnosis",
    "final_diagnosis",
}


def _strip_bias_fields(response: dict) -> dict:
    """Remove clinician bias fields from an adjudicator-bound timeline response."""
    for key in _CLINICIAN_BIAS_FIELDS:
        response.pop(key, None)

    if isinstance(response.get("longitudinal"), dict):
        for key in _CLINICIAN_BIAS_FIELDS:
            response["longitudinal"].pop(key, None)

    for visit in response.get("visits", []):
        if isinstance(visit.get("evidence"), dict):
            for key in _CLINICIAN_BIAS_FIELDS:
                visit["evidence"].pop(key, None)

    return response


@router.get("/assigned/{participant_id}")
def assigned_patient(participant_id:uuid.UUID,i=Depends(adjudicator),db:Session=Depends(get_db)):
    p=loaded(db,participant_id)
    if not p: raise HTTPException(404,"Assigned participant unavailable")
    _require_participant_scope(p, i)
    if not db.query(ReviewerAssignment).filter_by(participant_id=participant_id,reviewer_upn=i[0]).first(): raise HTTPException(403,"Participant is not assigned to this reviewer")
    if p.workflow_status!="ASSIGNED" or completion_state(db, p)[0]: raise HTTPException(404,"Assigned participant unavailable")
    audit(db,i[0],i[1],"PATIENT_DATA_ACCESSED","PARTICIPANT",p.id,{"portal":"ADJUDICATOR"}); db.commit()
    payload = timeline(p, db, i[0], include_assignments=False)
    if i[1] in ADJUDICATOR_ROLES:
        payload = _strip_bias_fields(payload)
    return payload


# ── Auto-assignment (MONITOR authority only) ──────────────────────────────────

class AutoAssignRequest(BaseModel):
    participant_id: str
    reason: Optional[str] = "Auto-assignment by system"


class DataQueryRequest(BaseModel):
    category: str = Field(min_length=3, max_length=60)
    query_text: str = Field(min_length=10, max_length=4000)
    visit_id: Optional[uuid.UUID] = None


class QueryResolutionRequest(BaseModel):
    response_text: str = Field(min_length=3, max_length=4000)
    closure_reason: str = Field(min_length=3, max_length=1000)


class RecusalRequest(BaseModel):
    reason_code: str = Field(min_length=3, max_length=50)
    comments: str = Field(min_length=10, max_length=2000)


class CorrectionRequest(BaseModel):
    raw_source_value: str = Field(min_length=1, max_length=4000)
    unit: Optional[str] = Field(default=None, max_length=40)
    observation_datetime: Optional[datetime] = None
    reason: str = Field(min_length=10, max_length=2000)


class CorrectionApprovalRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


def _correction_json(row):
    return {"id":str(row.id),"participant_id":str(row.participant_id),"original_observation_id":str(row.original_observation_id),"replacement_observation_id":str(row.replacement_observation_id) if row.replacement_observation_id else None,"proposed_values":row.proposed_values,"request_reason":row.request_reason,"requested_by":row.requested_by,"requested_at":row.requested_at,"status":row.status,"approval_reason":row.approval_reason,"approved_by":row.approved_by,"approved_at":row.approved_at}


@router.post("/observations/{observation_id}/corrections", status_code=201)
def request_observation_correction(observation_id: uuid.UUID, req: CorrectionRequest, i=Depends(monitor), db: Session=Depends(get_db)):
    original=db.get(CanonicalObservation,observation_id)
    if not original or original.prohibited_flag: raise HTTPException(404,"Observation not found")
    participant=db.get(LongitudinalParticipant,original.participant_id); _require_participant_scope(participant,i)
    if original.superseded: raise HTTPException(409,"Superseded observations cannot be corrected again; correct the active replacement")
    if db.query(ObservationCorrection).filter_by(original_observation_id=original.id,status="PENDING_APPROVAL").first():
        raise HTTPException(409,"A correction is already pending approval for this observation")
    proposed={"raw_source_value":req.raw_source_value.strip(),"unit":req.unit,"observation_datetime":req.observation_datetime.isoformat() if req.observation_datetime else None}
    row=ObservationCorrection(participant_id=participant.id,original_observation_id=original.id,proposed_values=proposed,request_reason=req.reason.strip(),requested_by=i[0])
    db.add(row); db.flush(); audit(db,i[0],i[1],"OBSERVATION_CORRECTION_REQUESTED","OBSERVATION_CORRECTION",row.id,{"participant_id":str(participant.id),"observation_id":str(original.id),"canonical_variable":original.canonical_variable})
    db.commit(); return _correction_json(row)


@router.get("/corrections")
def list_observation_corrections(status: Optional[str]=None, i=Depends(monitor), db: Session=Depends(get_db)):
    query=db.query(ObservationCorrection).join(LongitudinalParticipant,ObservationCorrection.participant_id==LongitudinalParticipant.id)
    query=_scope_participant_query(query,i)
    if status: query=query.filter(ObservationCorrection.status==status.upper())
    return [_correction_json(row) for row in query.order_by(ObservationCorrection.requested_at.desc()).all()]


@router.post("/corrections/{correction_id}/approve")
def approve_observation_correction(correction_id: uuid.UUID, req: CorrectionApprovalRequest, i=Depends(monitor), db: Session=Depends(get_db)):
    require_qc_monitor(i)
    correction=db.get(ObservationCorrection,correction_id)
    if not correction: raise HTTPException(404,"Correction not found")
    participant=db.get(LongitudinalParticipant,correction.participant_id); _require_participant_scope(participant,i)
    if correction.status!="PENDING_APPROVAL": raise HTTPException(409,"Correction is not pending approval")
    if correction.requested_by.strip().lower()==i[0].strip().lower(): raise HTTPException(409,"Correction approval requires a different authorized reviewer")
    original=db.get(CanonicalObservation,correction.original_observation_id)
    if not original or original.superseded: raise HTTPException(409,"Original observation is no longer active")
    proposed=correction.proposed_values; raw=proposed["raw_source_value"]
    observed=parse_datetime(proposed.get("observation_datetime")) if proposed.get("observation_datetime") else original.observation_datetime
    is_date=str(original.canonical_variable or "").lower().endswith(("date","datetime"))
    replacement=CanonicalObservation(participant_id=original.participant_id,visit_id=original.visit_id,source_batch_id=original.source_batch_id,canonical_variable=original.canonical_variable,raw_source_value=raw,parsed_text_value=raw,numeric_value=parse_numeric(raw),datetime_value=parse_datetime(raw) if is_date else None,coded_value=parse_coded(raw),unit=proposed.get("unit") or original.unit,observation_datetime=observed,date_confidence="EXACT" if observed else original.date_confidence,source_form=original.source_form,source_page=original.source_page,source_field_label=original.source_field_label,source_row_number=original.source_row_number,mapping_version=original.mapping_version,quality_status="VALID",documentation_status="Documented",provenance_type="SOURCE_CORRECTION",prohibited_flag=False,superseded=False,supersedes_observation_id=original.id,correction_id=correction.id,source_fingerprint=hashlib.sha256(json.dumps({"original":str(original.id),"correction":str(correction.id),"values":proposed},sort_keys=True).encode()).hexdigest())
    db.add(replacement); db.flush(); original.superseded=True
    correction.replacement_observation_id=replacement.id; correction.status="APPROVED"; correction.approval_reason=req.reason.strip(); correction.approved_by=i[0]; correction.approved_at=datetime.utcnow()
    visit=db.get(VisitInstance,original.visit_id)
    if original.canonical_variable in {"VISIT_DATE","visit_date"} and replacement.datetime_value: visit.visit_datetime=replacement.datetime_value
    db.flush(); derive_participant(db,participant,participant.visits)
    audit(db,i[0],i[1],"OBSERVATION_CORRECTION_APPROVED","OBSERVATION_CORRECTION",correction.id,{"participant_id":str(participant.id),"original_observation_id":str(original.id),"replacement_observation_id":str(replacement.id),"canonical_variable":original.canonical_variable})
    db.commit(); return _correction_json(correction)


def _reviewer_assignment(db, participant_id, reviewer_upn):
    return db.query(ReviewerAssignment).filter_by(
        participant_id=participant_id, reviewer_upn=reviewer_upn, status="ASSIGNED"
    ).first()


@router.post("/assigned/{participant_id}/queries", status_code=201)
def raise_data_query(participant_id: uuid.UUID, req: DataQueryRequest, i=Depends(adjudicator), db: Session=Depends(get_db)):
    participant = db.get(LongitudinalParticipant, participant_id)
    if not participant: raise HTTPException(404, "Assigned participant unavailable")
    _require_participant_scope(participant, i)
    assignment = _reviewer_assignment(db, participant_id, i[0])
    if not assignment: raise HTTPException(403, "Participant is not assigned to this reviewer")
    if req.visit_id and not db.query(VisitInstance).filter_by(id=req.visit_id, participant_id=participant_id).first():
        raise HTTPException(422, "visit_id is not part of this participant")
    row = ClinicalDataQuery(participant_id=participant_id, visit_id=req.visit_id, category=req.category.upper(), query_text=req.query_text.strip(), raised_by=i[0])
    db.add(row); db.flush()
    audit(db,i[0],i[1],"CLINICAL_DATA_QUERY_RAISED","DATA_QUERY",row.id,{"participant_id":str(participant_id),"category":row.category,"reviewer_role":assignment.reviewer_role})
    db.commit()
    return {"id":str(row.id),"status":row.status,"raised_at":row.raised_at}


@router.get("/queries")
def list_data_queries(status: Optional[str]=None, i=Depends(monitor), db: Session=Depends(get_db)):
    query = db.query(ClinicalDataQuery).join(LongitudinalParticipant, ClinicalDataQuery.participant_id == LongitudinalParticipant.id)
    query = _scope_participant_query(query, i)
    if status: query = query.filter(ClinicalDataQuery.status == status.upper())
    rows = query.order_by(ClinicalDataQuery.raised_at.desc()).all()
    participants = {p.id: p.blinded_subject_id for p in db.query(LongitudinalParticipant).filter(LongitudinalParticipant.id.in_([row.participant_id for row in rows])).all()} if rows else {}
    return [{"id":str(row.id),"participant_id":str(row.participant_id),"subject_id":participants.get(row.participant_id),"visit_id":str(row.visit_id) if row.visit_id else None,"category":row.category,"query_text":row.query_text,"raised_by":row.raised_by,"raised_at":row.raised_at,"status":row.status,"response_text":row.response_text,"responded_by":row.responded_by,"responded_at":row.responded_at,"closure_reason":row.closure_reason} for row in rows]


@router.post("/queries/{query_id}/resolve")
def resolve_data_query(query_id: uuid.UUID, req: QueryResolutionRequest, i=Depends(monitor), db: Session=Depends(get_db)):
    row = db.get(ClinicalDataQuery, query_id)
    if not row: raise HTTPException(404, "Data query not found")
    participant = db.get(LongitudinalParticipant, row.participant_id); _require_participant_scope(participant, i)
    if row.status == "CLOSED": raise HTTPException(409, "Data query is already closed")
    now=datetime.utcnow(); row.response_text=req.response_text.strip(); row.responded_by=i[0]; row.responded_at=now
    row.status="CLOSED"; row.closed_by=i[0]; row.closed_at=now; row.closure_reason=req.closure_reason.strip()
    audit(db,i[0],i[1],"CLINICAL_DATA_QUERY_CLOSED","DATA_QUERY",row.id,{"participant_id":str(row.participant_id),"closure_reason":row.closure_reason})
    db.commit(); return {"id":str(row.id),"status":row.status,"closed_at":row.closed_at}


@router.post("/assigned/{participant_id}/recuse", status_code=201)
def declare_recusal(participant_id: uuid.UUID, req: RecusalRequest, i=Depends(adjudicator), db: Session=Depends(get_db)):
    participant = db.get(LongitudinalParticipant, participant_id)
    if not participant: raise HTTPException(404, "Assigned participant unavailable")
    _require_participant_scope(participant, i)
    assignment = _reviewer_assignment(db, participant_id, i[0])
    if not assignment: raise HTTPException(403, "Participant is not assigned to this reviewer")
    canonical = db.query(Participant).filter((Participant.case_number==participant.blinded_subject_id)|(Participant.subject_id==participant.blinded_subject_id)).first()
    if canonical and db.query(AdjudicationRecord).filter_by(participant_id=canonical.id, reviewer_upn=i[0], signed=True).first():
        raise HTTPException(409, "A reviewer cannot recuse after signing; escalate for a controlled amendment")
    excluded={a.reviewer_upn for a in db.query(ReviewerAssignment).filter_by(participant_id=participant_id).all()}
    excluded.update(r.reviewer_upn for r in db.query(ReviewerRecusal).filter_by(participant_id=participant_id).all())
    from sqlalchemy import func as _func
    workloads=dict(db.query(ReviewerAssignment.reviewer_upn,_func.count(ReviewerAssignment.id)).filter_by(status="ASSIGNED").group_by(ReviewerAssignment.reviewer_upn).all())
    candidates=[u.email for u in db.query(PortalUser).filter_by(role="ADJUDICATOR",status="ACTIVE").all() if u.email not in excluded]
    if not _demo_contract_bypass_enabled():
        now = datetime.utcnow()
        contracted = {row[0] for row in db.query(AdjudicatorStudyContract.adjudicator_upn).filter(
            AdjudicatorStudyContract.study_code == participant.study,
            AdjudicatorStudyContract.status == "ACTIVE",
            AdjudicatorStudyContract.effective_from <= now,
            (AdjudicatorStudyContract.effective_to.is_(None) | (AdjudicatorStudyContract.effective_to > now)),
        ).all()}
        candidates = [email for email in candidates if email in contracted]
    if not candidates: raise HTTPException(409,"No independent replacement adjudicator is available")
    replacement=min(candidates,key=lambda upn:(workloads.get(upn,0),upn)); now=datetime.utcnow()
    recusal=ReviewerRecusal(participant_id=participant_id,assignment_id=assignment.id,reviewer_upn=i[0],reviewer_role=assignment.reviewer_role,reason_code=req.reason_code.upper(),comments=req.comments.strip(),replacement_upn=replacement,replacement_assigned_at=now)
    # The assignment slot is stable and unique per participant/role; recusal is
    # preserved in its own immutable record before the slot is transferred.
    assignment.reviewer_upn=replacement; assignment.status="ASSIGNED"; assignment.assigned_at=now
    db.add(recusal); db.flush()
    audit(db,i[0],i[1],"REVIEWER_RECUSED","PARTICIPANT",participant_id,{"reviewer_role":assignment.reviewer_role,"reason_code":recusal.reason_code,"replacement_upn":replacement})
    db.commit(); return {"id":str(recusal.id),"status":"RECUSED","replacement_assigned":True}


_AUTO_ASSIGN_CAP = ADJUDICATOR_CAPACITY_LIMIT


@router.post("/auto-assign", status_code=201)
def auto_assign(req: AutoAssignRequest, i=Depends(monitor), db: Session=Depends(get_db)):
    require_qc_monitor(i)
    """Assign the two least-loaded active adjudicators as REVIEWER_A and REVIEWER_B.

    Rules:
    - Only MONITOR-role callers may invoke this endpoint.
    - Each reviewer may hold at most _AUTO_ASSIGN_CAP active assignments.
    - Raises HTTP 409 when fewer than two eligible reviewers exist.
    - The same reviewer may not be assigned both slots.
    """
    try:
        participant_id = uuid.UUID(req.participant_id)
    except ValueError:
        raise HTTPException(422, "participant_id must be a valid UUID")

    p = db.get(LongitudinalParticipant, participant_id)
    if not p:
        raise HTTPException(404, "Participant not found")
    _require_participant_scope(p, i)
    if completion_state(db, p)[0]:
        raise HTTPException(409, "This case is already completed and cannot be auto-assigned")

    # Completed cases no longer consume capacity. Exclude this participant so
    # re-running auto-assignment can safely repair its existing slots.
    workloads = active_assignment_workloads(db, exclude_participant_id=p.id)

    adjudicators = (
        db.query(PortalUser)
        .filter_by(role="ADJUDICATOR", status="ACTIVE")
        .order_by(PortalUser.email)
        .all()
    )

    eligible = [
        u for u in adjudicators
        if workloads.get(u.email.strip().lower(), 0) < _AUTO_ASSIGN_CAP
    ]
    # Sort ascending by current workload so the least-loaded reviewers are picked first
    eligible.sort(key=lambda u: (workloads.get(u.email.strip().lower(), 0), u.email))

    if len(eligible) < 2:
        raise HTTPException(
            409,
            f"Auto-assignment failed: fewer than 2 eligible adjudicators available "
            f"(cap={_AUTO_ASSIGN_CAP} active cases). Rebalance the roster and retry."
        )

    reviewer_a_upn = eligible[0].email
    reviewer_b_upn = eligible[1].email

    for upn, role in ((reviewer_a_upn, "REVIEWER_A"), (reviewer_b_upn, "REVIEWER_B")):
        existing = db.query(ReviewerAssignment).filter_by(
            participant_id=p.id, reviewer_role=role
        ).first()
        if existing:
            existing.reviewer_upn = upn
            existing.status = "ASSIGNED"
            existing.assigned_at = datetime.utcnow()
        else:
            db.add(ReviewerAssignment(participant_id=p.id, reviewer_upn=upn, reviewer_role=role))

    if p.workflow_status not in {"ASSIGNED", "QC_APPROVED"}:
        p.workflow_status = "ASSIGNED"

    audit(
        db, i[0], i[1],
        "REVIEWER_AUTO_ASSIGNED", "PARTICIPANT", p.id,
        {
            "reviewer_a": reviewer_a_upn,
            "reviewer_b": reviewer_b_upn,
            "reason": req.reason,
            "cap": _AUTO_ASSIGN_CAP,
        },
    )
    db.commit()
    return {
        "status": "ASSIGNED",
        "participant_id": str(p.id),
        "reviewer_a": reviewer_a_upn,
        "reviewer_b": reviewer_b_upn,
        "reason": req.reason,
    }


# ── Configurable per-site/per-lab reference ranges (Monitor/QC authority only) ──

def rjson(r):
    return {"id":str(r.id),"analyte":r.analyte,"site_code":r.site_code,"lab_code":r.lab_code,"unit":r.unit,"low":r.low,"high":r.high,"is_active":r.is_active,"created_by":r.created_by,"updated_at":r.updated_at}


class ReferenceRangeRequest(BaseModel):
    analyte: str
    site_code: Optional[str] = None
    lab_code: Optional[str] = None
    unit: Optional[str] = None
    low: Optional[float] = None
    high: Optional[float] = None


@router.get("/reference-ranges")
def list_reference_ranges(i=Depends(monitor),db:Session=Depends(get_db)):
    rows=db.query(LabReferenceRange).order_by(LabReferenceRange.analyte,LabReferenceRange.site_code.nullsfirst()).all()
    return {"analytes":sorted(LAB_ANALYTES),"items":[rjson(r) for r in rows]}


@router.post("/reference-ranges",status_code=201)
def upsert_reference_range(req:ReferenceRangeRequest,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    analyte=req.analyte.strip().upper()
    if analyte not in LAB_ANALYTES:
        raise HTTPException(422,f"Unsupported analyte. Must be one of: {', '.join(sorted(LAB_ANALYTES))}")
    if req.low is None and req.high is None:
        raise HTTPException(422,"At least one of low/high must be provided")
    site_code=(req.site_code or "").strip().upper() or None
    lab_code=(req.lab_code or "").strip().upper() or None
    row=db.query(LabReferenceRange).filter_by(analyte=analyte,site_code=site_code,lab_code=lab_code).first()
    if row:
        row.unit=req.unit; row.low=req.low; row.high=req.high; row.is_active=True
    else:
        row=LabReferenceRange(analyte=analyte,site_code=site_code,lab_code=lab_code,unit=req.unit,low=req.low,high=req.high,created_by=i[0])
        db.add(row)
    db.flush(); audit(db,i[0],i[1],"LAB_REFERENCE_RANGE_SET","LAB_REFERENCE_RANGE",row.id,{"analyte":analyte,"site_code":site_code,"lab_code":lab_code,"low":req.low,"high":req.high}); db.commit()
    return rjson(row)


@router.post("/reference-ranges/{range_id}/deactivate")
def deactivate_reference_range(range_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    require_qc_monitor(i)
    row=db.get(LabReferenceRange,range_id)
    if not row: raise HTTPException(404,"Reference range not found")
    row.is_active=False
    audit(db,i[0],i[1],"LAB_REFERENCE_RANGE_DEACTIVATED","LAB_REFERENCE_RANGE",row.id); db.commit()
    return rjson(row)
