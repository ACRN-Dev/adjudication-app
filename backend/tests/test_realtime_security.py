"""RealTime API authorization tests: closes the header-trust bypass in backend/api/realtime.py.

This is the Monitor Portal's ACTUAL backend (the frontend calls /api/realtime/*, not
/api/monitor/*). Mirrors the pattern established in test_admin.py and test_monitor.py for
the sibling admin_security.py / monitor_security.py fixes.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import app
from models.auth import PortalUser
from services.auth_service import ACTIVE, hash_password
from conftest import TestingSession

client = TestClient(app)


def test_realtime_headers_rejected_when_demo_disabled_and_no_session(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/realtime/batches", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"})
    assert r.status_code == 401


def test_realtime_headers_accepted_when_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/realtime/batches", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"})
    assert r.status_code == 200


def test_realtime_session_with_valid_portal_role_grants_access(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.monitor@acrnhealth.com", display_name="SSO RealTime Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/realtime/batches", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_realtime_session_without_portal_role_rejected(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role.realtime@acrnhealth.com", display_name="No Portal Role RealTime",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role.realtime@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/realtime/batches", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403


def test_realtime_non_monitor_session_rejected_even_with_spoofed_headers(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.adjudicator@acrnhealth.com", display_name="SSO RealTime Adjudicator",
        password_hash=hash_password("Whatever123!"), role="ADJUDICATOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.adjudicator@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get(
        "/api/realtime/batches",
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
        headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"},
    )
    assert r.status_code == 403


def test_realtime_adjudicator_session_without_portal_role_can_reach_assigned(monkeypatch):
    """The whole reason actor()'s non-MONITOR branch has an explicit ADJUDICATOR allow-list:
    /assigned depends on actor() directly (not monitor()) and adjudicators typically have no
    portal_role at all. This must keep working after the allow-list tightening."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.adjudicator.noportal@acrnhealth.com", display_name="SSO RealTime Adjudicator No Portal Role",
        password_hash=hash_password("Whatever123!"), role="ADJUDICATOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.adjudicator.noportal@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/realtime/assigned", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_realtime_monitor_session_invalid_portal_role_definitive_even_when_demo_enabled_with_valid_headers(monkeypatch):
    """Proves the session's rejection isn't merely reachable-but-untested when demo mode is
    off (the earlier test only covered ENABLE_DEMO_ACCOUNTS=false, where headers are
    unreachable anyway). Here demo mode is ON and the accompanying headers are valid MONITOR
    credentials on their own -- the under-provisioned session must still win with a 403,
    never silently falling through to the headers."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.monitor.badportal@acrnhealth.com", display_name="SSO RealTime Monitor Bad Portal Role",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.monitor.badportal@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get(
        "/api/realtime/batches",
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
        headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"},
    )
    assert r.status_code == 403


def test_realtime_session_monitor_can_upload_batch(monkeypatch):
    import io, uuid
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.upload.monitor@acrnhealth.com", display_name="SSO Upload Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.upload.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200

    csv_content = (
        "MRN,Screening #,Randomization #,Form Title,Form Version,Page Title,Field type,Field Label,Data Input,Data Value,Audit Trails,Export Variable Name\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-001,RAND-001,Visit 1,v1.0,Vitals,text,Systolic Blood Pressure,120,120,,SBP\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-001,RAND-001,Visit 1,v1.0,Vitals,text,Diastolic Blood Pressure,80,80,,DBP\n"
    )
    files = {"file": ("test_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    r = client.post(
        "/api/realtime/batches",
        files=files,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["filename"] == "test_batch.csv"
    assert data["status"] in {"CHECKSUM_CALCULATED", "ROWS_STAGED", "VISITS_RECONSTRUCTED", "MONITOR_QC_REQUIRED"}


def test_realtime_session_admin_can_upload_batch(monkeypatch):
    import io, uuid
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.upload.admin@acrnhealth.com", display_name="SSO Upload Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.upload.admin@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200

    csv_content = (
        "MRN,Screening #,Randomization #,Form Title,Form Version,Page Title,Field type,Field Label,Data Input,Data Value,Audit Trails,Export Variable Name\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-002,RAND-002,Visit 1,v1.0,Vitals,text,Systolic Blood Pressure,130,130,,SBP\n"
    )
    files = {"file": ("admin_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    r = client.post(
        "/api/realtime/batches",
        files=files,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["filename"] == "admin_batch.csv"

