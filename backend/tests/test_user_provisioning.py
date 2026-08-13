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


def _login_as(email, display_name, portal_role):
    """Creates (if needed) and logs in as an ADMIN-role account with the given portal_role,
    so tests can exercise the fine-grained services.admin_security.ROLE_PERMISSIONS gate."""
    db = TestingSession()
    if not db.query(PortalUser).filter_by(email=email).first():
        db.add(PortalUser(
            email=email, display_name=display_name,
            password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role=portal_role, status=ACTIVE,
        ))
        db.commit()
    db.close()
    r = client.post("/api/auth/login", json={"email": email, "password": "Whatever123!"})
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


def test_set_role_clears_stale_portal_role():
    cookies = _login_as_admin()
    create = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "reroled.monitor@acrnhealth.com", "display_name": "Reroled Monitor",
            "role": "MONITOR", "portal_role": "MONITOR_QC_REVIEWER", "reason": "Setup",
        },
    )
    assert create.status_code == 201
    user_id = create.json()["id"]

    r = client.post(
        f"/api/auth/users/{user_id}/role", cookies=cookies,
        json={"role": "ADJUDICATOR", "reason": "Demoting from Monitor"},
    )
    assert r.status_code == 200
    assert r.json()["portal_role"] is None

    db = TestingSession()
    row = db.query(PortalUser).filter_by(id=user_id).first()
    assert row.portal_role is None
    db.close()


def test_admin_cannot_change_own_study_scope():
    cookies = _login_as_admin()
    db = TestingSession()
    admin_row = db.query(PortalUser).filter_by(email="provisioning.admin@acrnhealth.com").first()
    admin_id, original_scope = admin_row.id, admin_row.study_scope
    db.close()

    r = client.post(
        f"/api/auth/users/{admin_id}/study-scope", cookies=cookies,
        json={"study_scope": "*", "reason": "Self elevation attempt"},
    )
    assert r.status_code == 409

    db = TestingSession()
    assert db.query(PortalUser).filter_by(id=admin_id).first().study_scope == original_scope
    db.close()


def test_create_user_requires_users_manage_permission():
    from services.admin_security import ROLE_PERMISSIONS
    assert "users.manage" not in ROLE_PERMISSIONS["ACCESS_REVIEWER"]

    cookies = _login_as("readonly.admin@acrnhealth.com", "Readonly Admin", "ACCESS_REVIEWER")
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "blocked.user@acrnhealth.com", "display_name": "Blocked User", "role": "ADJUDICATOR", "reason": "Should be denied"},
    )
    assert r.status_code == 403


def test_admin_cannot_delegate_permissions_it_does_not_hold():
    """TECHNICAL_ADMIN has 'users.manage' (confirmed via ROLE_PERMISSIONS) but not the full
    ADMIN permission set, so it can provision users but cannot create a new full-ADMIN
    account -- that would delegate permissions (e.g. studies.manage, access.approve) the
    acting admin doesn't itself hold. It can still create a MONITOR user, since the
    delegation check in create_user only applies when role == "ADMIN"."""
    from services.admin_security import ROLE_PERMISSIONS
    assert "users.manage" in ROLE_PERMISSIONS["TECHNICAL_ADMIN"]
    assert not ROLE_PERMISSIONS["ADMIN"] <= ROLE_PERMISSIONS["TECHNICAL_ADMIN"]

    cookies = _login_as("delegating.admin@acrnhealth.com", "Delegating Admin", "TECHNICAL_ADMIN")

    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "overreach.admin@acrnhealth.com", "display_name": "Overreach Admin",
            "role": "ADMIN", "portal_role": "ADMIN", "reason": "Attempting to delegate full ADMIN",
        },
    )
    assert r.status_code == 403

    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "fine.monitor@acrnhealth.com", "display_name": "Fine Monitor",
            "role": "MONITOR", "portal_role": "MONITOR_QC_REVIEWER", "reason": "No delegation check for MONITOR",
        },
    )
    assert r.status_code == 201
