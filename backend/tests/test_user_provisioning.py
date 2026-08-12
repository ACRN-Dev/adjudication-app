import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from conftest import TestingSession
from main import app
from models.auth import PortalUser
from services.auth_service import ACTIVE, hash_password

client = TestClient(app)


def _login_as_admin():
    db = TestingSession()
    if not db.query(PortalUser).filter_by(email="provisioning.admin@acrnhealth.com").first():
        db.add(PortalUser(
            email="provisioning.admin@acrnhealth.com", display_name="Provisioning Admin",
            password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
        ))
        db.commit()
    db.close()
    r = client.post("/api/auth/login", json={"email": "provisioning.admin@acrnhealth.com", "password": "Whatever123!"})
    assert r.status_code == 200
    return {"acrn_demo_session": r.cookies["acrn_demo_session"]}


def test_admin_can_create_sso_managed_user_without_password():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "new.sso.monitor@acrnhealth.com", "display_name": "New SSO Monitor",
            "role": "MONITOR", "portal_role": "MONITOR_QC_REVIEWER", "study_scope": "PROTECT-Africa",
            "reason": "Provisioning for Microsoft SSO pilot",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "Monitor"
    assert body["portal_role"] == "MONITOR_QC_REVIEWER"
    assert body["study_scope"] == "PROTECT-Africa"

    db = TestingSession()
    row = db.query(PortalUser).filter_by(email="new.sso.monitor@acrnhealth.com").first()
    assert row.password_hash is None
    db.close()


def test_create_user_rejects_duplicate_email():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "provisioning.admin@acrnhealth.com", "display_name": "Dup", "role": "ADJUDICATOR", "reason": "Duplicate test"},
    )
    assert r.status_code == 409


def test_create_admin_requires_valid_portal_role():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "bad.role@acrnhealth.com", "display_name": "Bad Role", "role": "ADMIN", "portal_role": "NOT_A_REAL_ROLE", "reason": "Invalid role test"},
    )
    assert r.status_code == 422


def test_set_study_scope_updates_existing_user():
    cookies = _login_as_admin()
    create = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "scope.test@acrnhealth.com", "display_name": "Scope Test", "role": "MONITOR", "portal_role": "QA_REVIEWER", "reason": "Scope test setup"},
    )
    user_id = create.json()["id"]
    r = client.post(f"/api/auth/users/{user_id}/study-scope", cookies=cookies, json={"study_scope": "LOPE-Nigeria", "reason": "Narrowing scope"})
    assert r.status_code == 200
    assert r.json()["study_scope"] == "LOPE-Nigeria"


def test_admin_cannot_change_own_portal_role():
    cookies = _login_as_admin()
    db = TestingSession()
    admin_row = db.query(PortalUser).filter_by(email="provisioning.admin@acrnhealth.com").first()
    admin_id, original_role = admin_row.id, admin_row.portal_role
    db.close()

    r = client.post(
        f"/api/auth/users/{admin_id}/portal-role", cookies=cookies,
        json={"portal_role": "CLINICAL_OPS_ADMIN", "reason": "Self elevation attempt"},
    )
    assert r.status_code == 409

    db = TestingSession()
    assert db.query(PortalUser).filter_by(id=admin_id).first().portal_role == original_role
    db.close()


def test_create_user_rejects_blank_study_scope():
    cookies = _login_as_admin()
    for label, blank in [("empty", ""), ("comma", ",")]:
        r = client.post(
            "/api/auth/users", cookies=cookies,
            json={
                "email": f"blank.{label}.scope@acrnhealth.com", "display_name": "Blank Scope",
                "role": "MONITOR", "portal_role": "QA_REVIEWER", "study_scope": blank,
                "reason": "Blank scope test",
            },
        )
        assert r.status_code == 422


def test_set_study_scope_rejects_blank_value():
    cookies = _login_as_admin()
    create = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "blank.update.scope@acrnhealth.com", "display_name": "Blank Update Scope", "role": "MONITOR", "portal_role": "QA_REVIEWER", "reason": "Setup"},
    )
    user_id = create.json()["id"]
    for blank in ["", ","]:
        r = client.post(f"/api/auth/users/{user_id}/study-scope", cookies=cookies, json={"study_scope": blank, "reason": "Blank scope attempt"})
        assert r.status_code == 422


def test_study_scope_normalizes_whitespace_around_commas():
    cookies = _login_as_admin()
    create = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "space.scope@acrnhealth.com", "display_name": "Space Scope", "role": "MONITOR",
            "portal_role": "QA_REVIEWER", "study_scope": "PROTECT-Africa, LOPE-Nigeria", "reason": "Setup",
        },
    )
    assert create.status_code == 201
    assert create.json()["study_scope"] == "PROTECT-Africa,LOPE-Nigeria"

    user_id = create.json()["id"]
    r = client.post(
        f"/api/auth/users/{user_id}/study-scope", cookies=cookies,
        json={"study_scope": "  LOPE-Nigeria ,  PROTECT-Africa  ", "reason": "Re-normalize"},
    )
    assert r.status_code == 200
    assert r.json()["study_scope"] == "LOPE-Nigeria,PROTECT-Africa"
