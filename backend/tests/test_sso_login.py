import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from conftest import TestingSession
from main import app
from models.auth import AuthAuditEvent, PortalUser
from services.auth_service import ACTIVE

client = TestClient(app)


def _set_sso_env():
    os.environ["ENTRA_CLIENT_ID"] = "test-client-id"
    os.environ["ENTRA_CLIENT_SECRET"] = "test-secret"
    os.environ["ENTRA_TENANT_ID"] = "test-tenant-id"
    os.environ["APP_BASE_URL"] = "https://adjudication-test.acrncloud.com"


@patch("api.auth._sso_app")
def test_sso_login_redirects_to_microsoft_with_state_cookie(mock_sso_app):
    _set_sso_env()
    mock_client = MagicMock()
    mock_client.get_authorization_request_url.return_value = (
        "https://login.microsoftonline.com/test-tenant-id/oauth2/v2.0/authorize?client_id=test-client-id"
    )
    mock_sso_app.return_value = mock_client
    r = client.get("/api/auth/sso/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "login.microsoftonline.com" in r.headers["location"]
    assert "acrn_sso_state" in r.cookies


def test_sso_callback_rejects_state_mismatch():
    _set_sso_env()
    r = client.get("/api/auth/sso/callback?code=abc&state=wrong", cookies={"acrn_sso_state": "right"})
    assert r.status_code == 400


@patch("api.auth._sso_app")
def test_sso_callback_creates_session_for_registered_user(mock_sso_app):
    _set_sso_env()
    db = TestingSession()
    db.add(PortalUser(
        email="ssoadmin@acrnhealth.com", display_name="SSO Admin", password_hash=None,
        role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()

    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {"preferred_username": "ssoadmin@acrnhealth.com", "name": "SSO Admin"}
    }
    mock_sso_app.return_value = mock_client

    r = client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "acrn_demo_session" in r.cookies

    db = TestingSession()
    assert db.query(AuthAuditEvent).filter_by(event_type="SSO_LOGIN_SUCCESS").count() == 1
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_rejects_unregistered_email(mock_sso_app):
    _set_sso_env()
    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {"preferred_username": "unknown.person@acrnhealth.com", "name": "Unknown Person"}
    }
    mock_sso_app.return_value = mock_client

    r = client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "sso_error=not_registered" in r.headers["location"]
    assert "acrn_demo_session" not in r.cookies
