"""Admin Portal authorization, scope, versioning, blinding, audit and demo tests."""
from datetime import datetime, timedelta
import os, sys
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["ENABLE_DEMO_ACCOUNTS"] = "true"
os.environ["ENABLE_DEMO_DATA"] = "true"
from main import app
from models.admin import AdminUser, ControlledVersion, AdminAuditEvent
from models.auth import PortalUser
from models.canonical import ImportBatch, Participant, SubjectAssignment, AdjudicationVisit, AdjudicationRecord, ReviewerRole, StudyCode
from models.longitudinal import RTImportBatch, LongitudinalParticipant, ReviewerAssignment
from services.admin_security import Identity, validate_mapping, validate_workflow_definition, risk_warnings
from services.auth_service import ACTIVE, hash_password
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


def test_admin_headers_rejected_when_demo_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/admin/dashboard", headers=CLIN)
    assert r.status_code == 401


def test_admin_session_grants_access_using_portal_role(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.tech.admin@acrnhealth.com", display_name="SSO Tech Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.tech.admin@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/admin/dashboard", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_admin_session_without_portal_role_denied(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role@acrnhealth.com", display_name="No Portal Role",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/admin/dashboard", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403


def test_sso_admin_can_reset_demo_data_without_demo_accounts(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    monkeypatch.setenv("ENABLE_DEMO_DATA", "true")
    db = TestingSession()
    db.add(PortalUser(
        email="demo.data.admin@acrnhealth.com", display_name="Demo Data Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "demo.data.admin@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    response = client.post(
        "/api/admin/demo/reset",
        json={"reason": "Reset synthetic data for the hosted demonstration"},
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert response.status_code == 200


def test_reset_all_is_scoped_to_csv_imports_and_assignments(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_DATA", "true")
    db = TestingSession()
    admin_email = "scoped.reset.admin@acrnhealth.com"
    if not db.query(PortalUser).filter_by(email=admin_email).first():
        db.add(PortalUser(
            email=admin_email, display_name="Scoped Reset Admin",
            password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
        ))

    csv_batch = ImportBatch(study=StudyCode.EOPE, edc_filename="scenario-a.csv", mapping_version="test", imported_by=admin_email)
    retained_batch = ImportBatch(study=StudyCode.EOPE, edc_filename="production-feed.json", mapping_version="test", imported_by=admin_email)
    db.add_all([csv_batch, retained_batch])
    db.flush()
    csv_participant = Participant(subject_id="CSV-RESET-001", case_number="ADJ-CSV-001", study=StudyCode.EOPE, import_batch_id=csv_batch.id)
    retained_participant = Participant(subject_id="KEEP-RESET-001", case_number="ADJ-KEEP-001", study=StudyCode.EOPE, import_batch_id=retained_batch.id)
    db.add_all([csv_participant, retained_participant])
    db.flush()
    csv_visit = AdjudicationVisit(participant_id=csv_participant.id, visit_number=1, visit_code="V01")
    retained_visit = AdjudicationVisit(participant_id=retained_participant.id, visit_number=1, visit_code="V01")
    db.add_all([csv_visit, retained_visit])
    db.flush()
    db.add_all([
        SubjectAssignment(participant_id=csv_participant.id, reviewer_a_upn="a@demo", reviewer_b_upn="b@demo"),
        SubjectAssignment(participant_id=retained_participant.id, reviewer_a_upn="a@demo", reviewer_b_upn="b@demo"),
        AdjudicationRecord(participant_id=csv_participant.id, visit_id=csv_visit.id, reviewer_role=ReviewerRole.REVIEWER_A, reviewer_upn="a@demo"),
        AdjudicationRecord(participant_id=retained_participant.id, visit_id=retained_visit.id, reviewer_role=ReviewerRole.REVIEWER_A, reviewer_upn="a@demo"),
    ])

    rt_csv = RTImportBatch(filename="scenario-b.csv", checksum="scoped-reset-csv", file_size=1, uploaded_by=admin_email)
    rt_retained = RTImportBatch(filename="production-feed.parquet", checksum="scoped-reset-keep", file_size=1, uploaded_by=admin_email)
    db.add_all([rt_csv, rt_retained])
    db.flush()
    rt_csv_participant = LongitudinalParticipant(blinded_subject_id="RT-CSV-001", source_batch_id=rt_csv.id)
    rt_retained_participant = LongitudinalParticipant(blinded_subject_id="RT-KEEP-001", source_batch_id=rt_retained.id)
    db.add_all([rt_csv_participant, rt_retained_participant])
    db.flush()
    db.add_all([
        ReviewerAssignment(participant_id=rt_csv_participant.id, reviewer_upn="a@demo", reviewer_role="REVIEWER_A"),
        ReviewerAssignment(participant_id=rt_retained_participant.id, reviewer_upn="a@demo", reviewer_role="REVIEWER_A"),
    ])
    db.commit()
    db.close()

    login = client.post("/api/auth/login", json={"email": admin_email, "password": "Whatever123!"})
    response = client.post(
        "/api/admin/demo/reset-all",
        json={"reason": "Scoped CSV reset regression"},
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert response.status_code == 200

    db = TestingSession()
    assert db.query(PortalUser).filter_by(email=admin_email).count() == 1
    assert db.query(ImportBatch).filter_by(edc_filename="scenario-a.csv").count() == 0
    assert db.query(Participant).filter_by(subject_id="CSV-RESET-001").count() == 0
    assert db.query(ImportBatch).filter_by(edc_filename="production-feed.json").count() == 1
    assert db.query(Participant).filter_by(subject_id="KEEP-RESET-001").count() == 1
    assert db.query(SubjectAssignment).join(Participant).filter(Participant.subject_id == "KEEP-RESET-001").count() == 1
    assert db.query(RTImportBatch).filter_by(filename="scenario-b.csv").count() == 0
    assert db.query(LongitudinalParticipant).filter_by(blinded_subject_id="RT-CSV-001").count() == 0
    assert db.query(RTImportBatch).filter_by(filename="production-feed.parquet").count() == 1
    assert db.query(LongitudinalParticipant).filter_by(blinded_subject_id="RT-KEEP-001").count() == 1
    assert db.query(ReviewerAssignment).join(LongitudinalParticipant).filter(LongitudinalParticipant.blinded_subject_id == "RT-KEEP-001").count() == 1
    db.close()
