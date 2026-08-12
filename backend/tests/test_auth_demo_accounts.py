import os, sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import Base, get_db
from main import app
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import DEMO_ACCOUNTS, default_password, maybe_seed_demo_accounts, seed_demo_accounts, verify_password
from conftest import TestingSession


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_auth_db_override():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def reset_auth_tables():
    db = TestingSession()
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in {"portal_users", "auth_sessions", "auth_audit_events"}:
            db.execute(table.delete())
    db.commit()
    return db


def test_demo_seed_is_idempotent_and_passwords_are_hashed():
    db = reset_auth_tables()
    assert seed_demo_accounts(db) == 6
    assert seed_demo_accounts(db) == 0
    users = db.query(PortalUser).all()
    assert len(users) == len(DEMO_ACCOUNTS)
    assert all(u.password_hash != default_password() for u in users)
    assert verify_password(default_password(), users[0].password_hash)
    db.close()


def test_all_demo_accounts_can_login_and_route_to_expected_portal():
    db = reset_auth_tables()
    seed_demo_accounts(db)
    db.close()
    expected = {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator"}
    for email, _, role in DEMO_ACCOUNTS:
        r = client.post("/api/auth/login", json={"email": email.upper(), "password": default_password()})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == email
        assert body["roleCode"] == role
        assert body["portal"] == expected[role]
        assert default_password() not in str(body)


def test_invalid_login_is_generic_and_locks_account():
    db = reset_auth_tables()
    seed_demo_accounts(db)
    db.close()
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "monitor1@acrnhealth.com", "password": "wrong"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid email or password."
    assert client.post("/api/auth/login", json={"email": "monitor1@acrnhealth.com", "password": default_password()}).status_code == 401
    db = TestingSession()
    assert db.query(AuthAuditEvent).filter_by(event_type="ACCOUNT_LOCK").count() == 1
    db.close()


def test_role_boundaries_and_logout_invalidate_access():
    db = reset_auth_tables()
    seed_demo_accounts(db)
    db.close()
    monitor = TestClient(app)
    assert monitor.post("/api/auth/login", json={"email": "monitor2@acrnhealth.com", "password": default_password()}).status_code == 200
    assert monitor.get("/api/auth/users").status_code == 403
    assert monitor.get("/api/admin/dashboard").status_code == 403
    assert monitor.post("/api/auth/logout").status_code == 200
    assert monitor.get("/api/auth/me").status_code == 401


def test_maybe_seed_demo_accounts_respects_enable_flag(monkeypatch):
    db = reset_auth_tables()
    monkeypatch.delenv("ENABLE_DEMO_ACCOUNTS", raising=False)
    maybe_seed_demo_accounts(db)
    assert db.query(PortalUser).filter_by(email="admin@acrnhealth.com").first() is None

    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    maybe_seed_demo_accounts(db)
    assert db.query(PortalUser).filter_by(email="admin@acrnhealth.com").first() is not None
    db.close()


def test_admin_account_actions_audit_and_do_not_leak_default_password():
    db = reset_auth_tables()
    seed_demo_accounts(db)
    target = db.query(PortalUser).filter_by(email="adjudicatora@acrnhealth.com").first().id
    db.close()
    admin = TestClient(app)
    assert admin.post("/api/auth/login", json={"email": "admin@acrnhealth.com", "password": default_password()}).status_code == 200
    assert admin.post(f"/api/auth/users/{target}/status", json={"status": "INACTIVE", "reason": "Demo test"}).status_code == 200
    assert admin.post(f"/api/auth/users/{target}/role", json={"role": "MONITOR", "reason": "Demo test"}).status_code == 200
    assert admin.post(f"/api/auth/users/{target}/reset-password", json={"reason": "Demo reset"}).status_code == 200
    body = admin.get("/api/auth/users").json()
    assert default_password() not in str(body)
    db = TestingSession()
    events = {x.event_type for x in db.query(AuthAuditEvent).all()}
    assert {"ACCOUNT_DEACTIVATION", "ROLE_CHANGE", "PASSWORD_RESET"} <= events
    db.close()
