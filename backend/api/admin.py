"""Protected operational APIs for the non-clinical ACRN Admin Portal."""
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db, DB_OFFLINE
from models.admin import AdminUser, AdminRole, UserRole, StudyAccess, AdminStudy, AdminSite, ControlledVersion, IntegrationStatus, AdminAuditEvent, AccessReview
from services.admin_demo import seed_demo, reset_demo
from services.admin_security import Identity, get_identity, require, enforce_study, validate_delegation, risk_warnings, validate_mapping, validate_workflow_definition, add_audit

router = APIRouter()
ACTIVE_STATUSES = {"Active","Approved","Scheduled"}

class ReasonedRequest(BaseModel): reason: str = Field(min_length=3); effective_at: Optional[datetime] = None
class UserCreate(ReasonedRequest):
    display_name: str; email: str; organisation: str = "ACRN Foundation"; country: str; job_title: str = ""; role_codes: list[str] = []; study_codes: list[str] = []; access_expiry: Optional[datetime] = None
class AccessDecision(ReasonedRequest): approved: bool; target_user_email: str
class VersionCreate(ReasonedRequest):
    resource_type: str; code: str; name: str; version: str; study_codes: list[str] = []; definition: dict[str,Any] = {}; supporting_reference: Optional[str] = None
class VersionStatus(ReasonedRequest): status: str
class StudyCreate(ReasonedRequest):
    study_code: str; name: str; protocol_number: str = ""; protocol_version: str = ""; endpoint_type: str = ""; countries: list[str] = []; status: str = "Draft"
class SiteCreate(ReasonedRequest):
    site_code: str; blinded_name: str; country: str; study_code: str; status: str = "Draft"; import_identifier: str = ""; source_types: list[str] = []
class ReviewCreate(ReasonedRequest): name: str; scope_type: str; scope_value: str; reviewer_upn: str; due_at: datetime

def serialize(row):
    return {c.name: getattr(row,c.name) for c in row.__table__.columns}
def boot(db): seed_demo(db)

@router.get("/me")
def me(identity: Identity=Depends(get_identity)):
    return {"upn":identity.upn,"role":identity.role,"permissions":sorted(identity.permissions),"study_scope":identity.studies,"authentication_source":identity.auth_source,"production_security":False,"clinical_case_access":False}

@router.get("/dashboard")
def dashboard(identity: Identity=Depends(require("admin.read")), db: Session=Depends(get_db)):
    boot(db); now=datetime.utcnow(); users=db.query(AdminUser).filter(AdminUser.is_demo.is_(True)).all(); versions=db.query(ControlledVersion).filter(ControlledVersion.is_demo.is_(True)).all(); integrations=db.query(IntegrationStatus).filter(IntegrationStatus.is_demo.is_(True)).all()
    return {"demo":True,"environment":"DEMO / STANDALONE","database":"SQLite fallback" if DB_OFFLINE else "PostgreSQL","api":"Healthy","metrics":{"active_studies":db.query(AdminStudy).filter_by(status="Active",is_demo=True).count(),"configured_sites":db.query(AdminSite).filter_by(is_demo=True).count(),"active_users":sum(u.status=="Active" for u in users),"pending_approval":sum(u.status=="Pending approval" for u in users),"expiring_access":sum(bool(u.access_expiry and u.access_expiry<now+timedelta(days=60)) for u in users),"incomplete_training":sum(u.training_status!="Current" for u in users),"open_access_reviews":db.query(AccessReview).filter_by(status="Open",is_demo=True).count(),"active_rules":sum(v.resource_type=="RULE" and v.status=="Active" for v in versions),"draft_rules":sum(v.resource_type=="RULE" and v.status in ("Draft","Under review") for v in versions),"mapping_failures":sum(v.resource_type=="MAPPING" and v.test_status=="Failed" for v in versions),"integration_warnings":sum(i.status in ("Warning","Failed") for i in integrations)},"action_queue":[{"type":"ACCESS_APPROVAL","label":"Approve pending user access","count":sum(u.status=="Pending approval" for u in users)},{"type":"EXPIRY","label":"Review access expiring within 60 days","count":sum(bool(u.access_expiry and u.access_expiry<now+timedelta(days=60)) for u in users)},{"type":"TRAINING","label":"Review incomplete training","count":sum(u.training_status!="Current" for u in users)},{"type":"INTEGRATION","label":"Resolve integration warnings","count":sum(i.status=="Warning" for i in integrations)}]}

@router.get("/users")
def users(search:str="",status:str="",page:int=1,page_size:int=25,identity:Identity=Depends(require("users.read")),db:Session=Depends(get_db)):
    boot(db); q=db.query(AdminUser).filter(AdminUser.is_demo.is_(True));
    if search: q=q.filter((AdminUser.display_name.ilike(f"%{search}%"))|(AdminUser.email.ilike(f"%{search}%")))
    if status: q=q.filter(AdminUser.status==status)
    total=q.count(); rows=q.order_by(AdminUser.display_name).offset((page-1)*page_size).limit(min(page_size,100)).all(); return {"demo":True,"total":total,"page":page,"items":[serialize(r) for r in rows]}

@router.post("/users",status_code=201)
def create_user(req:UserCreate,identity:Identity=Depends(require("users.manage")),db:Session=Depends(get_db)):
    validate_delegation(identity, set().union(*(set(__import__('services.admin_security',fromlist=['ROLE_PERMISSIONS']).ROLE_PERMISSIONS.get(r,set())) for r in req.role_codes)))
    if db.query(AdminUser).filter_by(email=req.email).first(): raise HTTPException(409,"User already exists")
    row=AdminUser(display_name=req.display_name,email=req.email,organisation=req.organisation,country=req.country,job_title=req.job_title,status="Pending approval",access_expiry=req.access_expiry,created_by=identity.upn,is_demo=True); db.add(row); db.flush()
    for rc in req.role_codes: db.add(UserRole(user_id=row.id,role_code=rc,assigned_by=identity.upn,reason=req.reason,is_demo=True))
    for sc in req.study_codes: enforce_study(identity,sc); db.add(StudyAccess(user_id=row.id,study_code=sc,status="Pending approval",requested_by=identity.upn,reason=req.reason,is_demo=True))
    add_audit(db,identity,"USER_CREATED","USER",row.id,req.reason,new={"email":req.email,"roles":req.role_codes}); db.commit(); return {**serialize(row),"risk_warnings":risk_warnings(req.role_codes)}

@router.post("/users/{user_id}/access-decision")
def access_decision(user_id:str,req:AccessDecision,identity:Identity=Depends(require("access.approve")),db:Session=Depends(get_db)):
    if req.target_user_email.lower()==identity.upn.lower(): raise HTTPException(409,"Users cannot approve their own access.")
    row=db.get(AdminUser,user_id)
    if not row: raise HTTPException(404,"User not found")
    old=row.status; row.status="Active" if req.approved else "Deactivated"; row.approved_by=identity.upn if req.approved else None; row.status_reason=req.reason
    add_audit(db,identity,"ACCESS_APPROVED" if req.approved else "ACCESS_REJECTED","USER",row.id,req.reason,previous={"status":old},new={"status":row.status}); db.commit(); return serialize(row)

@router.post("/users/{user_id}/status")
def user_status(user_id:str,req:VersionStatus,identity:Identity=Depends(require("users.manage")),db:Session=Depends(get_db)):
    if req.status not in {"Suspended","Active","Deactivated","Expired"}: raise HTTPException(422,"Unsupported account status")
    row=db.get(AdminUser,user_id)
    if not row: raise HTTPException(404,"User not found")
    old=row.status; row.status=req.status; row.status_reason=req.reason
    if req.status=="Deactivated": row.deactivated_by=identity.upn
    add_audit(db,identity,f"USER_{req.status.upper()}","USER",row.id,req.reason,previous={"status":old},new={"status":req.status}); db.commit(); return serialize(row)

@router.get("/roles")
def roles(identity:Identity=Depends(require("roles.read")),db:Session=Depends(get_db)):
    boot(db); rows=db.query(AdminRole).filter_by(is_demo=True).order_by(AdminRole.code).all(); return {"demo":True,"items":[{**serialize(r),"risk_combinations":[w for p,w in __import__('services.admin_security',fromlist=['HIGH_RISK']).HIGH_RISK if r.code in p]} for r in rows]}

@router.get("/studies")
def studies(identity:Identity=Depends(require("admin.read")),db:Session=Depends(get_db)):
    boot(db); rows=db.query(AdminStudy).filter_by(is_demo=True).order_by(AdminStudy.study_code,AdminStudy.version.desc()).all(); return {"demo":True,"items":[serialize(r) for r in rows if not identity.studies or "*" in identity.studies or r.study_code in identity.studies]}
@router.post("/studies",status_code=201)
def create_study(req:StudyCreate,identity:Identity=Depends(require("studies.manage")),db:Session=Depends(get_db)):
    enforce_study(identity,req.study_code); latest=db.query(AdminStudy).filter_by(study_code=req.study_code).order_by(AdminStudy.version.desc()).first(); version=(latest.version+1) if latest else 1
    row=AdminStudy(study_code=req.study_code,version=version,name=req.name,protocol_number=req.protocol_number,protocol_version=req.protocol_version,endpoint_type=req.endpoint_type,countries=req.countries,status="Draft",environment="DEMO",change_reason=req.reason,is_demo=True); db.add(row); add_audit(db,identity,"STUDY_VERSION_CREATED","STUDY",req.study_code,req.reason,new={"version":version}); db.commit(); return serialize(row)

@router.get("/sites")
def sites(study_code:Optional[str]=None,identity:Identity=Depends(require("admin.read")),db:Session=Depends(get_db)):
    boot(db); enforce_study(identity,study_code); q=db.query(AdminSite).filter_by(is_demo=True); q=q.filter_by(study_code=study_code) if study_code else q; return {"demo":True,"items":[serialize(r) for r in q.all() if not identity.studies or "*" in identity.studies or r.study_code in identity.studies]}
@router.post("/sites",status_code=201)
def create_site(req:SiteCreate,identity:Identity=Depends(require("sites.manage")),db:Session=Depends(get_db)):
    enforce_study(identity,req.study_code); row=AdminSite(**req.model_dump(exclude={"reason","effective_at"}),is_demo=True); db.add(row); add_audit(db,identity,"SITE_CREATED","SITE",req.site_code,req.reason,new={"study_code":req.study_code,"blinded_name":req.blinded_name},study_code=req.study_code); db.commit(); return serialize(row)

@router.get("/versions/{resource_type}")
def versions(resource_type:str,identity:Identity=Depends(require("admin.read")),db:Session=Depends(get_db)):
    boot(db); rows=db.query(ControlledVersion).filter_by(resource_type=resource_type.upper(),is_demo=True).order_by(ControlledVersion.code,ControlledVersion.created_at.desc()).all(); return {"demo":True,"items":[serialize(r) for r in rows if not identity.studies or "*" in identity.studies or not r.study_codes or set(r.study_codes)&set(identity.studies)]}
@router.post("/versions",status_code=201)
def create_version(req:VersionCreate,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    perm={"RULE":"rules.manage","MAPPING":"mappings.manage","FORM":"forms.manage","WORKFLOW":"workflows.manage"}.get(req.resource_type.upper())
    if not perm or perm not in identity.permissions: raise HTTPException(403,"Version management permission denied")
    for study in req.study_codes: enforce_study(identity,study)
    if req.resource_type.upper()=="MAPPING": validate_mapping(req.definition)
    if req.resource_type.upper()=="WORKFLOW": validate_workflow_definition(req.definition)
    row=ControlledVersion(resource_type=req.resource_type.upper(),code=req.code,name=req.name,version=req.version,study_codes=req.study_codes,status="Draft",definition=req.definition,supporting_reference=req.supporting_reference,test_status="Not run",change_reason=req.reason,is_demo=True); db.add(row); add_audit(db,identity,f"{req.resource_type.upper()}_VERSION_CREATED",req.resource_type.upper(),req.code,req.reason,new={"version":req.version}); db.commit(); return serialize(row)
@router.post("/versions/{version_id}/status")
def version_status(version_id:str,req:VersionStatus,identity:Identity=Depends(get_identity),db:Session=Depends(get_db)):
    row=db.get(ControlledVersion,version_id)
    if not row: raise HTTPException(404,"Version not found")
    perm={"RULE":"rules.manage","MAPPING":"mappings.manage","FORM":"forms.manage","WORKFLOW":"workflows.manage"}.get(row.resource_type)
    if perm not in identity.permissions and not (req.status=="Approved" and f"{row.resource_type.lower()}s.approve" in identity.permissions): raise HTTPException(403,"Version status permission denied")
    if row.status=="Active": raise HTTPException(409,"Active versions are immutable; create a successor draft version.")
    if req.status in {"Approved","Scheduled","Active"} and row.test_status!="Passed": raise HTTPException(409,"Version cannot activate until validation tests pass.")
    if row.resource_type=="RULE" and req.status in {"Scheduled","Active"} and not (row.clinical_approved_by and row.qa_approved_by): raise HTTPException(409,"Rule activation requires clinical and QA approvals.")
    old=row.status; row.status=req.status; add_audit(db,identity,f"{row.resource_type}_STATUS_CHANGED",row.resource_type,row.id,req.reason,previous={"status":old},new={"status":req.status}); db.commit(); return serialize(row)

@router.get("/integrations")
def integrations(identity:Identity=Depends(require("admin.read")),db:Session=Depends(get_db)):
    boot(db); return {"demo":True,"items":[serialize(r) for r in db.query(IntegrationStatus).filter_by(is_demo=True).all()]}
@router.get("/audit")
def audit(action:str="",study_code:str="",limit:int=100,identity:Identity=Depends(require("audit.read")),db:Session=Depends(get_db)):
    boot(db); enforce_study(identity,study_code or None); q=db.query(AdminAuditEvent).filter_by(is_demo=True); q=q.filter_by(action=action) if action else q; q=q.filter_by(study_code=study_code) if study_code else q; return {"demo":True,"immutable":True,"items":[serialize(r) for r in q.order_by(AdminAuditEvent.timestamp.desc()).limit(min(limit,500)).all()]}
@router.get("/access-reviews")
def access_reviews(identity:Identity=Depends(require("access.review")),db:Session=Depends(get_db)):
    boot(db); return {"demo":True,"items":[serialize(r) for r in db.query(AccessReview).filter_by(is_demo=True).all()]}
@router.post("/access-reviews",status_code=201)
def create_review(req:ReviewCreate,identity:Identity=Depends(require("access.review")),db:Session=Depends(get_db)):
    row=AccessReview(name=req.name,scope_type=req.scope_type,scope_value=req.scope_value,reviewer_upn=req.reviewer_upn,due_at=req.due_at,is_demo=True); db.add(row); add_audit(db,identity,"ACCESS_REVIEW_CREATED","ACCESS_REVIEW",row.id,req.reason,new={"scope":req.scope_value}); db.commit(); return serialize(row)
@router.get("/reports/{report_code}")
def report(report_code:str,identity:Identity=Depends(require("reports.read")),db:Session=Depends(get_db)):
    allowed={"user-access","role-permissions","study-register","rule-versions","mapping-versions","form-register","access-reviews","training-compliance","configuration-changes","integration-incidents","import-failures","audit-summary"}
    if report_code not in allowed: raise HTTPException(404,"Unknown administrative report")
    add_audit(db,identity,"REPORT_EXPORTED","REPORT",report_code,"Controlled administrative report generated",new={"scope":identity.studies}); db.commit(); return {"demo":True,"report":report_code,"generated_at":datetime.utcnow(),"study_scope":identity.studies,"note":"Synthetic demonstration report; production export adapter not connected."}
@router.post("/demo/reset")
def demo_reset(req:ReasonedRequest,identity:Identity=Depends(require("integrations.manage")),db:Session=Depends(get_db)):
    counts=reset_demo(db); add_audit(db,identity,"DEMO_ADMIN_DATA_RESET","DEMO_DATA","administration",req.reason,new=counts); db.commit(); return {"demo":True,"reset":counts,"production_records_affected":0}
