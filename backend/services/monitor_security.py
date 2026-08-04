import hashlib,json
from dataclasses import dataclass
from datetime import datetime,timezone
from fastapi import Header,HTTPException,Depends
from models.monitor import MonitorAuditEvent
ROLES={"ADJUDICATION_COORDINATOR","MONITOR_QC_REVIEWER","QA_REVIEWER","RELEASE_OPERATOR"}
PROHIBITED=("sflt-1","sflt1","plgf","seng","biomarker","poc result","treatment allocation","randomisation","randomization")
@dataclass(frozen=True)
class MonitorIdentity: upn:str; role:str; studies:tuple[str,...]
def identity(x_demo_user:str|None=Header(None),x_demo_role:str|None=Header(None),x_study_scope:str|None=Header(None)):
    if not x_demo_user or not x_demo_role: raise HTTPException(401,"Authentication required")
    if x_demo_role.upper() not in ROLES: raise HTTPException(403,"Monitor Portal access denied")
    return MonitorIdentity(x_demo_user,x_demo_role.upper(),tuple(filter(None,(x_study_scope or "").split(","))))
def scope(i,study):
    if i.studies and "*" not in i.studies and study not in i.studies: raise HTTPException(403,"Study outside delegated scope")
def scan_blinding(names,content=""):
    text=" ".join(names)+" "+content
    hits=sorted({p for p in PROHIBITED if p in text.lower()})
    return {"passed":not hits,"hits":hits,"state":"CLEARED" if not hits else "UNBLINDING_QUARANTINE"}
def validate_import(filename,checksum,headers,rows,existing):
    if checksum in existing: raise HTTPException(409,"Duplicate file checksum")
    if not rows: raise HTTPException(422,"Import requires one or more data rows")
    if not {"participant_id"}<=set(headers): raise HTTPException(422,"Required participant identifier missing")
    scan=scan_blinding([filename,*headers]);
    if not scan["passed"]: raise HTTPException(422,{"message":"Prohibited content quarantined","scan":scan})
    return True
def qc_gate(items):
    failed=[x for x in items if x.get("mandatory") and x.get("response")!="Pass"]
    if failed: raise HTTPException(409,"Mandatory pre-QC items must pass before release")
def assignment_gate(a,b,eligible):
    if a==b: raise HTTPException(409,"Reviewer A and B must be different people")
    if a not in eligible or b not in eligible: raise HTTPException(409,"Reviewer eligibility check failed")
def release_gate(final_qc,committee_locked=True):
    if final_qc!="Pass" or not committee_locked: raise HTTPException(409,"Final QC and required committee lock must complete before release")
def audit(db,i,action,entity,eid,study,reason,details=None,outcome="SUCCESS"):
    raw=f"{datetime.now(timezone.utc).isoformat()}|{i.upn}|{action}|{eid}"
    db.add(MonitorAuditEvent(actor_upn=i.upn,actor_role=i.role,action=action,entity_type=entity,entity_id=eid,study_code=study,reason=reason,outcome=outcome,details=details or {},record_hash=hashlib.sha256(raw.encode()).hexdigest(),is_demo=True))

