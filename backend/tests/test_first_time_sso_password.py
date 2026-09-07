"""
Test: SSO-only accounts (no password yet) can set an initial password without
providing a "current password" (there isn't one), and the endpoint still
requires proof of the current password once one exists.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from conftest import TestingSession
from database import get_db
from main import app
from models.auth import PortalUser
from services.auth_service import ACTIVE, hash_password

client = TestClient(app)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _login_cookie(email):
    db = TestingSession()
    db.commit()
    db.close()
    r = client.post("/api/auth/login", json={"email": email, "password": "ACRN@2026-existing"})
    return r


def test_sso_only_account_can_set_first_password_without_current_password():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        email = "sso.first.password@acrnhealth.com"
        db = TestingSession()
        db.query(PortalUser).filter_by(email=email).delete()
        db.add(PortalUser(
            email=email, display_name="SSO First Password", password_hash=None,
            role="ADJUDICATOR", status=ACTIVE, must_change_password=True,
        ))
        db.commit()
        user_id = db.query(PortalUser).filter_by(email=email).first().id
        db.close()

        # Log in via a valid session by issuing one directly (SSO path already tested elsewhere).
        from services.auth_service import issue_session
        from fastapi import Response
        db = TestingSession()
        user = db.get(PortalUser, user_id)
        resp = Response()
        issue_session(db, user, resp, None, "SSO_LOGIN_SUCCESS")
        cookie_header = resp.headers.get("set-cookie", "")
        token = cookie_header.split("acrn_demo_session=")[1].split(";")[0]
        db.close()

        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "", "new_password": "ACRN@2026-new-strong"},
            cookies={"acrn_demo_session": token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["must_change_password"] is False
        assert body["has_password"] is True

        db = TestingSession()
        assert db.query(PortalUser).filter_by(email=email).first().must_change_password is False
        db.close()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_change_password_still_requires_correct_current_password_when_one_exists():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        email = "sso.has.password@acrnhealth.com"
        db = TestingSession()
        db.query(PortalUser).filter_by(email=email).delete()
        db.add(PortalUser(
            email=email, display_name="Has Password", password_hash=hash_password("ACRN@2026-existing"),
            role="ADJUDICATOR", status=ACTIVE, must_change_password=False,
        ))
        db.commit()
        user_id = db.query(PortalUser).filter_by(email=email).first().id
        db.close()

        from services.auth_service import issue_session
        from fastapi import Response
        db = TestingSession()
        user = db.get(PortalUser, user_id)
        resp = Response()
        issue_session(db, user, resp, None, "LOGIN_SUCCESS")
        cookie_header = resp.headers.get("set-cookie", "")
        token = cookie_header.split("acrn_demo_session=")[1].split(";")[0]
        db.close()

        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong-password", "new_password": "ACRN@2026-new-strong"},
            cookies={"acrn_demo_session": token},
        )
        assert r.status_code == 401, r.text
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
