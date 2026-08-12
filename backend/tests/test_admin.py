"""Admin Portal authorization, scope, versioning, blinding, audit and demo tests."""
from datetime import datetime, timedelta
import os, sys
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import app
from models.admin import AdminUser, ControlledVersion, AdminAuditEvent
from services.admin_security import Identity, validate_mapping, validate_workflow_definition, risk_warnings
from conftest import TestingSession

client=TestClient(app)
CLIN={"X-Demo-User":"clinical.ops.demo@acrnhealth.com","X-Demo-Role":"CLINICAL_OPS_ADMIN","X-Study-Scope":"PROTECT-Africa,LOPE-Nigeria"}
TECH={"X-Demo-User":"tech.admin.demo@acrnhealth.com","X-Demo-Role":"TECHNICAL_ADMIN","X-Study-Scope":"*"}

def test_admin_route_requires_authentication(): assert client.get("/api/admin/dashboard").status_code==401
def test_direct_url_denied_to_adjudicator(): assert client.get("/api/admin/dashboard",headers={"X-Demo-User":"reviewer@demo","X-Demo-Role":"ADJUDICATOR"}).status_code==403
def test_admin_identity_never_grants_clinical_content(): assert client.get("/api/admin/me",headers=TECH).json()["clinical_case_access"] is False
def test_study_scope_enforced():
    h={**CLIN,"X-Study-Scope":"PROTECT-Africa"}
    assert client.get("/api/admin/sites?study_code=LOPE-Nigeria",headers=h).status_code==403
def test_self_approval_prevented():
    r=client.post("/api/admin/users/demo-user-clinops/access-decision",headers=CLIN,json={"reason":"Self approval attempt","approved":True,"target_user_email":"clinical.ops.demo@acrnhealth.com"})
    assert r.status_code==409
def test_high_risk_role_warning(): assert "Technical administrator plus adjudicator" in risk_warnings(["TECHNICAL_ADMIN","ADJUDICATOR"])
def test_user_suspension_is_audited():
    r=client.post("/api/admin/users/demo-user-pending/status",headers=TECH,json={"reason":"Periodic security review","status":"Suspended"})
    assert r.status_code==200 and r.json()["status"]=="Suspended"
    db=TestingSession(); assert db.query(AdminAuditEvent).filter_by(action="USER_SUSPENDED").count()>=1; db.close()
def test_access_expiry_persisted():
    expiry=(datetime.utcnow()+timedelta(days=30)).isoformat()
    r=client.post("/api/admin/users",headers=TECH,json={"reason":"Approved demonstration invitation","display_name":"Expiry Test","email":"expiry.test@demo.local","country":"Ghana","role_codes":[],"study_codes":[],"access_expiry":expiry})
    assert r.status_code==201 and r.json()["access_expiry"] is not None
@pytest.mark.parametrize("kind",["RULE","MAPPING","FORM"])
def test_active_controlled_versions_are_immutable(kind):
    db=TestingSession(); row=ControlledVersion(resource_type=kind,code=f"IMM-{kind}",name="Immutable",version="1.0",status="Active",definition={},test_status="Passed",change_reason="test",is_demo=True); db.add(row); db.commit(); rid=row.id; db.close()
    permission_headers=CLIN
    r=client.post(f"/api/admin/versions/{rid}/status",headers=permission_headers,json={"reason":"Attempted in-place edit","status":"Retired"})
    assert r.status_code==409
def test_prohibited_field_mapping_rejected():
    for field in ["sFlt-1","PlGF","sEng","treatment_allocation"]:
        with pytest.raises(HTTPException): validate_mapping({"source_field":field,"canonical_field":"clinical_value"})
def test_invalid_workflow_transition_rejected():
    with pytest.raises(HTTPException): validate_workflow_definition({"states":["Imported","Reviewer In Progress"],"transitions":[{"source":"Imported","target":"Reviewer In Progress"}]})
def test_audit_events_immutable():
    db=TestingSession(); row=db.query(AdminAuditEvent).first(); row.reason="tampered"
    with pytest.raises(ValueError): db.commit()
    db.rollback(); db.close()
def test_demo_data_separated_and_marked():
    r=client.get("/api/admin/users",headers=TECH); assert r.status_code==200 and r.json()["demo"] is True
    db=TestingSession(); assert all(x.is_demo for x in db.query(AdminUser).all()); db.close()
def test_delegated_authority_prevents_excess_permissions():
    payload={"reason":"Excess grant attempt","display_name":"Bad Grant","email":"bad.grant@demo.local","country":"Ghana","role_codes":["CLINICAL_OPS_ADMIN"],"study_codes":[]}
    assert client.post("/api/admin/users",headers=TECH,json=payload).status_code==403
