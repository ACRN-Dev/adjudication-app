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
