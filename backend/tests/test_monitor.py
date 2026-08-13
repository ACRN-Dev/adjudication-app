import os,sys,pytest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from services.monitor_security import scan_blinding,validate_import,qc_gate,assignment_gate,release_gate
from services.workflow_policy import check_reviewer_isolation,check_committee_quorum,evaluate_concordance
from conftest import TestingSession

client = TestClient(app)


def test_prohibited_fields_quarantined(): assert scan_blinding(['export_PlGF.csv'])['state']=='UNBLINDING_QUARANTINE'
def test_clean_blinded_file_passes(): assert scan_blinding(['edc_bp.csv'])['passed']
def test_duplicate_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','same',['participant_id'],[{'participant_id':'1'}],{'same'})
def test_empty_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['participant_id'],[],set())
def test_required_header_enforced():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['bp'],[{'bp':120}],set())
def test_mandatory_pre_qc_blocks_release():
    with pytest.raises(HTTPException): qc_gate([{'mandatory':True,'response':'Fail'}])
def test_pre_qc_passes(): qc_gate([{'mandatory':True,'response':'Pass'},{'mandatory':False,'response':'N/A'}])
def test_same_reviewer_cannot_fill_both_roles():
    with pytest.raises(HTTPException): assignment_gate('a','a',{'a'})
def test_ineligible_reviewer_rejected():
    with pytest.raises(HTTPException): assignment_gate('a','b',{'a'})
def test_reviewer_isolation_preserved(): assert check_reviewer_isolation('A','B','QA_RELEASED') is False
def test_concordance_and_discordance():
    a={'primary_diagnosis':'PE','onset_classification':'EOPE','severity_phenotype':'severe','certainty_level':'definite'}
    assert evaluate_concordance(a,a)['concordant']; b={**a,'certainty_level':'probable'}; assert not evaluate_concordance(a,b)['concordant']
def test_committee_quorum_gate(): assert not check_committee_quorum(2).allowed and check_committee_quorum(3).allowed
def test_final_qc_gate():
    with pytest.raises(HTTPException): release_gate('Fail',True)
    with pytest.raises(HTTPException): release_gate('Pass',False)
    release_gate('Pass',True)


def test_monitor_headers_rejected_when_demo_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 401


def test_monitor_headers_accepted_when_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 200


def test_monitor_session_grants_access_using_portal_role(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    db = TestingSession()
    db.add(PortalUser(
        email="sso.monitor@acrnhealth.com", display_name="SSO Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200
    assert r.json()["role"] == "MONITOR_QC_REVIEWER"


def test_monitor_session_without_portal_role_denied(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role.monitor@acrnhealth.com", display_name="No Portal Role Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403

