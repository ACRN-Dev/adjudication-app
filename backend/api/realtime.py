"""Secure RealTime import, Monitor database, and assigned-case API."""
import os, uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter,UploadFile,File,BackgroundTasks,Depends,HTTPException,Header,Query,Request
from pydantic import BaseModel
from sqlalchemy.orm import Session,selectinload
from database import get_db
from models.longitudinal import RTImportBatch,LongitudinalParticipant,VisitInstance,ImportIssue,ReviewerAssignment,LongitudinalCaseDerivation,LabReferenceRange
from models.history import PatientHistoryField, PatientRiskSummary
from services.realtime_pipeline import checksum_file,process_batch,audit
from services.auth_service import current_user, audit_auth
from services.lab_reference import evaluate_participant_labs, LAB_ANALYTES
from models.auth import PortalUser
from models.admin import AdjudicatorStudyContract
router = APIRouter()
MONITOR = {"ADJUDICATION_COORDINATOR", "MONITOR_QC_REVIEWER", "QA_REVIEWER", "RELEASE_OPERATOR", "MONITOR", "ADMIN"}

def actor(request: Request, x_demo_user: str | None = Header(None), x_demo_role: str | None = Header(None), db: Session = Depends(get_db)):
    token = request.cookies.get("acrn_demo_session")
    if token:
        from services.auth_service import _hash_token
        from models.auth import AuthSession
        from services.monitor_security import ROLES as MONITOR_PORTAL_ROLES
        s = db.query(AuthSession).filter_by(token_hash=_hash_token(token), revoked_at=None).first()
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
        if u.role == "MONITOR":
            pr = u.portal_role
            if not pr or pr not in MONITOR_PORTAL_ROLES:
                return u.email, "MONITOR", False
            return u.email, pr, True
        if u.role == "ADMIN":
            return u.email, "ADMIN", True
        if u.role in {"ADJUDICATOR", "CHAIRPERSON"}:
            return u.email, u.role, False
        raise HTTPException(403, "Monitor/QC authority required")
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
                "adjudicatora@acrnhealth.com": "ADJUDICATOR",
                "adjudicatorb@acrnhealth.com": "ADJUDICATOR",
                "adjudicatorc@acrnhealth.com": "ADJUDICATOR",
            }
            if not demo_user and known_demo.get(claimed_email) == claimed_role:
                return claimed_email, claimed_role, claimed_role == "MONITOR"
            if not demo_user or not demo_user.is_demo_account:
                raise HTTPException(401, detail={"message": "Unrecognized demo identity.", "reason": "no_session"})
            if demo_user.must_change_password:
                raise HTTPException(403, detail={"code": "PASSWORD_CHANGE_REQUIRED", "message": "You must set a new password before continuing."})
            if demo_user.role != claimed_role and not (demo_user.role == "ADJUDICATOR" and claimed_role in {"REVIEWER_A", "REVIEWER_B"}):
                raise HTTPException(403, detail={"message": "Role mismatch for demo identity.", "reason": "role_mismatch"})
            is_qc = claimed_role in MONITOR or demo_user.role in {"MONITOR", "ADMIN"}
            return demo_user.email, claimed_role, is_qc
    raise HTTPException(401, detail={"message": "Authentication required. Please sign in.", "reason": "no_session"})


def authenticated(i = Depends(actor)):
    """The RealTime batch import and the reconstructed-participant views are open to every
    authenticated account, whatever its role. QC decisions still go through monitor()."""
    return i


def monitor(i = Depends(actor)):
    if not i[2]:
        raise HTTPException(403, "Monitor/QC authority required — portal role not provisioned. Contact your administrator.")
    return i


# Coarse, monotonically increasing progress estimate for the async batch pipeline.
_STAGE_PCT = {
    "UPLOADED": 5, "CHECKSUM_CALCULATED": 10, "STRUCTURE_VALIDATION": 20, "ROWS_STAGED": 30,
    "VISITS_RECONSTRUCTED": 85, "MONITOR_QC_REQUIRED": 100, "FAILED": 100, "CANCELLED": 100,
}


def _progress_pct(b):
    base = _STAGE_PCT.get(b.status, 0)
    if b.status == "ROWS_STAGED" and b.row_count:
        # Interpolate within the row-processing stage using rows_processed/row_count.
        frac = min(1.0, (b.rows_processed or 0) / max(1, b.row_count))
        return int(30 + frac * 55)
    return base


def bjson(b): return {"id":str(b.id),"filename":b.filename,"checksum":b.checksum,"file_size":b.file_size,"uploaded_at":b.uploaded_at,"rows":b.row_count,"rows_processed":b.rows_processed,"participants":b.participant_count,"visits":b.visit_count,"mapping_version":b.mapping_version,"status":b.status,"progress_pct":_progress_pct(b),"validation_result":b.validation_result,"blinding_result":b.blinding_result,"errors":b.error_count,"warnings":b.warning_count,"prohibited_excluded":b.prohibited_count,"finished_at":b.processing_finished_at}
@router.post("/batches",status_code=202)
async def upload(background:BackgroundTasks,file:UploadFile=File(...),i=Depends(authenticated),db:Session=Depends(get_db)):
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(415,"RealTime import requires CSV")
    staging=os.path.join(os.path.dirname(os.path.dirname(__file__)),".rt-staging"); os.makedirs(staging,exist_ok=True)
    path=os.path.join(staging,f"{uuid.uuid4()}.csv"); size=0
    with open(path,"wb") as out:
        while chunk:=await file.read(1024*1024): size+=len(chunk); out.write(chunk)
    checksum=checksum_file(path); existing=db.query(RTImportBatch).filter_by(checksum=checksum).first()
    if existing: os.remove(path); raise HTTPException(409,{"message":"Exact duplicate file","batch_id":str(existing.id)})
    b=RTImportBatch(filename=os.path.basename(file.filename),checksum=checksum,file_size=size,uploaded_by=i[0],source_path=path,status="CHECKSUM_CALCULATED")
    db.add(b); db.flush(); audit(db,i[0],i[1],"BATCH_UPLOADED","IMPORT_BATCH",b.id,{"filename":b.filename,"size":size,"checksum":checksum}); db.commit(); background.add_task(process_batch,b.id); return bjson(b)
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
            db.add(b); db.flush(); audit(db,i[0],i[1],"BATCH_UPLOADED","IMPORT_BATCH",b.id,{"filename":b.filename,"size":size,"checksum":checksum,"bulk":True}); db.commit()
            background.add_task(process_batch,b.id)
            entry.update(status="QUEUED",batch=bjson(b)); results.append(entry)
        except Exception as exc:
            db.rollback(); entry.update(status="ERROR",error=str(exc)); results.append(entry)
    return {"total":len(files),"accepted":sum(1 for r in results if r["status"]=="QUEUED"),"items":results}
@router.get("/batches")
def batches(i=Depends(authenticated),db:Session=Depends(get_db)): return [bjson(x) for x in db.query(RTImportBatch).order_by(RTImportBatch.uploaded_at.desc()).all()]
@router.get("/batches/{batch_id}")
def batch(batch_id:uuid.UUID,i=Depends(authenticated),db:Session=Depends(get_db)):
    b=db.get(RTImportBatch,batch_id)
    if not b: raise HTTPException(404,"Batch not found")
    return bjson(b)
@router.post("/batches/{batch_id}/cancel")
def cancel(batch_id:uuid.UUID,i=Depends(authenticated),db:Session=Depends(get_db)):
    b=db.get(RTImportBatch,batch_id)
    if not b or b.status in {"PUBLISHED","SUPERSEDED"}: raise HTTPException(409,"Batch cannot be cancelled")
    b.cancel_requested=True; audit(db,i[0],i[1],"IMPORT_CANCEL_REQUESTED","IMPORT_BATCH",b.id); db.commit(); return {"status":"CANCEL_REQUESTED"}
def pjson(p):
    assignments = []
    try:
        if hasattr(p, "reviewer_assignments") and p.reviewer_assignments:
            assignments = [{"reviewer_upn": a.reviewer_upn, "reviewer_role": a.reviewer_role} for a in p.reviewer_assignments]
    except Exception:
        assignments = []
    return {
        "id":str(p.id),
        "subject_id":p.blinded_subject_id,
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
        "assignments": assignments
    }
@router.get("/patients")
def patients(page:int=1,page_size:int=100,search:str="",qc_status:str="",i=Depends(authenticated),db:Session=Depends(get_db)):
    page_val = int(page.default if hasattr(page, 'default') else page)
    size_val = int(page_size.default if hasattr(page_size, 'default') else page_size)
    q=db.query(LongitudinalParticipant)
    if search:q=q.filter(LongitudinalParticipant.blinded_subject_id.ilike(f"%{search}%"))
    if qc_status:q=q.filter_by(workflow_status=qc_status)
    total=q.count()
    items=q.order_by(LongitudinalParticipant.blinded_subject_id).offset((page_val-1)*size_val).limit(size_val).all()
    return {"page":page_val,"page_size":size_val,"total":total,"items":[{**pjson(p),"lab_issues":evaluate_participant_labs(db,p)} for p in items]}
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
def timeline(p,db):
    visits=[]
    for v in sorted(p.visits,key=lambda x:(x.visit_datetime is None,x.visit_datetime or datetime.max,x.visit_sequence)):
        evidence={}
        for o in v.observations:
            if o.prohibited_flag or o.canonical_variable.startswith("RECORDED_PE_"): continue
            evidence.setdefault(o.canonical_variable,[]).append({"value":o.numeric_value if o.numeric_value is not None else o.coded_value or o.parsed_text_value,"unit":o.unit,"observed_at":o.observation_datetime,"date_confidence":o.date_confidence,"provenance":o.provenance_type,"source":{"form":o.source_form,"page":o.source_page,"field":o.source_field_label,"row":o.source_row_number}})
        visits.append({"id":str(v.id),"name":v.scheduled_visit_code,"occurrence":v.visit_occurrence,"date":v.visit_datetime,"ga_days":v.gestational_age_days,"form":v.form_title,"form_version":v.form_version,"reconstruction":{"method":v.reconstruction_method,"confidence":v.reconstruction_confidence,"qc_status":v.qc_status},"evidence":evidence})
    d=db.query(LongitudinalCaseDerivation).filter_by(participant_id=p.id).first()
    long=None if not d else {"earliest_qualifying_date":d.earliest_qualifying_pe_date,"first_qualifying_visit_id":str(d.first_qualifying_visit_id) if d.first_qualifying_visit_id else None,"onset_classification":d.onset_classification,"maximum_severity":d.maximum_severity,"packet_completeness":d.packet_completeness,"certainty_restriction":d.certainty_restriction,"trigger_status":d.trigger_status,"recorded_site_diagnosis":d.recorded_site_diagnosis,"recorded_site_diagnosis_date":d.recorded_site_diagnosis_date,"discrepancy":d.recorded_versus_derived_discrepancy,"explanation":d.explanation}
    history_fields = db.query(PatientHistoryField).filter_by(participant_id=p.id).order_by(PatientHistoryField.domain, PatientHistoryField.instance_index, PatientHistoryField.field_key).all()
    history = {"obstetric": [], "conditions": [], "medications": [], "medical": [], "family": [], "allergy_surgery": []}
    for f in history_fields:
        item = history_item(f)
        if f.domain in history:
            history[f.domain].append(item)
        if f.domain == "conditions":
            history["medical"].append(item)
        elif f.domain in {"medical", "family", "allergy_surgery"}:
            history["conditions"].append(item)
    rs = db.query(PatientRiskSummary).filter_by(participant_id=p.id).first()
    risk_summary = {"chips": rs.chips if rs else [], "parity_summary": rs.parity_summary if rs else "", "gravidity": rs.gravidity if rs else 0, "parity": rs.parity if rs else 0, "miscarriages": rs.miscarriages if rs else 0, "stillbirths": rs.stillbirths if rs else 0, "vaginal_deliveries": rs.vaginal_deliveries if rs else 0, "c_sections": rs.c_sections if rs else 0, "chronic_htn": rs.chronic_htn if rs else False, "pregestational_diabetes": rs.pregestational_diabetes if rs else False}
    return {**pjson(p),"visits":visits,"longitudinal":long,"history":history,"risk_summary":risk_summary}
@router.get("/patients/{participant_id}")
def patient(participant_id:uuid.UUID,i=Depends(authenticated),db:Session=Depends(get_db)):
    p=loaded(db,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    # Record the caller's actual authority, not a hardcoded portal: this view is reachable
    # by every role now, so a fixed "MONITOR" would misattribute the access.
    audit(db,i[0],i[1],"PATIENT_DATA_ACCESSED","PARTICIPANT",p.id,{"portal":"MONITOR" if i[2] else "NON_QC","role":i[1]}); db.commit(); return {**timeline(p,db),"lab_issues":evaluate_participant_labs(db,p)}
@router.post("/patients/{participant_id}/approve")
def approve(participant_id:uuid.UUID,i=Depends(monitor),db:Session=Depends(get_db)):
    p=db.get(LongitudinalParticipant,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    if db.query(ImportIssue).filter_by(participant_id=p.id,resolution_status="OPEN").count(): raise HTTPException(409,"Unresolved import issues block approval")
    p.workflow_status="QC_APPROVED"; audit(db,i[0],i[1],"PARTICIPANT_QC_APPROVED","PARTICIPANT",p.id); db.commit(); return {"status":p.workflow_status}
@router.post("/patients/{participant_id}/assign")
def assign(participant_id:uuid.UUID,reviewer_upn:str,reviewer_role:str,i=Depends(monitor),db:Session=Depends(get_db)):
    p=db.get(LongitudinalParticipant,participant_id)
    if not p: raise HTTPException(404,"Participant not found")
    if p.workflow_status=="MONITOR_QC_REQUIRED": p.workflow_status="QC_APPROVED"
    if reviewer_role not in {"REVIEWER_A","REVIEWER_B"}: raise HTTPException(422,"Invalid reviewer role")
    reviewer_upn=reviewer_upn.strip().lower()
    reviewer=db.query(PortalUser).filter_by(email=reviewer_upn,role="ADJUDICATOR",status="ACTIVE").first()
    if not reviewer: raise HTTPException(422,f"Reviewer '{reviewer_upn}' must be an active adjudicator account")
    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() != "true":
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
    p.workflow_status="ASSIGNED"; audit(db,i[0],i[1],"REVIEWER_ASSIGNED","PARTICIPANT",p.id,{"reviewer_role":reviewer_role,"reviewer_upn":reviewer_upn}); db.commit(); return {"status":"ASSIGNED"}
@router.get("/assigned")
def assigned(i=Depends(actor),db:Session=Depends(get_db)):
    if i[1] not in {"ADJUDICATOR","REVIEWER_A","REVIEWER_B"}: raise HTTPException(403,"Adjudicator role required")
    rows=db.query(ReviewerAssignment,LongitudinalParticipant).join(LongitudinalParticipant,ReviewerAssignment.participant_id==LongitudinalParticipant.id).filter(ReviewerAssignment.reviewer_upn==i[0],LongitudinalParticipant.workflow_status=="ASSIGNED").all()
    return [pjson(p) for _,p in rows]

@router.get("/adjudicators")
def adjudicators(i=Depends(monitor), db:Session=Depends(get_db)):
    """Active roster; A/B are positional slots, never fixed identities."""
    rows = db.query(PortalUser).filter_by(role="ADJUDICATOR", status="ACTIVE").order_by(PortalUser.display_name).all()
    workloads=dict(db.query(ReviewerAssignment.reviewer_upn, __import__('sqlalchemy').func.count(ReviewerAssignment.id)).filter_by(status="ASSIGNED").group_by(ReviewerAssignment.reviewer_upn).all())
    return [{"email": u.email, "display_name": u.display_name, "portal_role": u.portal_role,
             "active_workload": workloads.get(u.email,0)} for u in rows]
@router.get("/assigned/{participant_id}")
def assigned_patient(participant_id:uuid.UUID,i=Depends(actor),db:Session=Depends(get_db)):
    if not db.query(ReviewerAssignment).filter_by(participant_id=participant_id,reviewer_upn=i[0]).first(): raise HTTPException(403,"Participant is not assigned to this reviewer")
    p=loaded(db,participant_id)
    if not p or p.workflow_status!="ASSIGNED": raise HTTPException(404,"Assigned participant unavailable")
    audit(db,i[0],i[1],"PATIENT_DATA_ACCESSED","PARTICIPANT",p.id,{"portal":"ADJUDICATOR"}); db.commit(); return timeline(p,db)


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
    row=db.get(LabReferenceRange,range_id)
    if not row: raise HTTPException(404,"Reference range not found")
    row.is_active=False
    audit(db,i[0],i[1],"LAB_REFERENCE_RANGE_DEACTIVATED","LAB_REFERENCE_RANGE",row.id); db.commit()
    return rjson(row)
