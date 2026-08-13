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

    mock_client.get_authorization_request_url.assert_called_once()
    call_args = mock_client.get_authorization_request_url.call_args
    assert call_args.args[0] == ["User.Read"]
    assert call_args.kwargs["state"] == r.cookies["acrn_sso_state"]
    assert call_args.kwargs["redirect_uri"] == "https://adjudication-test.acrncloud.com/api/auth/sso/callback"


def test_sso_login_redirects_to_not_configured_when_entra_env_missing(monkeypatch):
    monkeypatch.delenv("ENTRA_CLIENT_ID", raising=False)
    monkeypatch.delenv("ENTRA_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ENTRA_TENANT_ID", raising=False)
    os.environ["APP_BASE_URL"] = "https://adjudication-test.acrncloud.com"
    r = client.get("/api/auth/sso/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "sso_error=not_configured" in r.headers["location"]
    assert "acrn_sso_state" not in r.cookies


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


def _sso_callback(mock_sso_app, email, name="Some Person"):
    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {"preferred_username": email, "name": name}
    }
    mock_sso_app.return_value = mock_client
    return client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )


@patch("api.auth._sso_app")
def test_sso_callback_auto_provisions_unknown_tenant_user_as_adjudicator(mock_sso_app):
    _set_sso_env()
    r = _sso_callback(mock_sso_app, "blessward.mutsotso@acrnhealth.com", "Blessward Mutsotso")

    assert r.status_code in (302, 307)
    assert "sso_error" not in r.headers["location"]
    assert "acrn_demo_session" in r.cookies

    db = TestingSession()
    user = db.query(PortalUser).filter_by(email="blessward.mutsotso@acrnhealth.com").one()
    assert user.role == "ADJUDICATOR"
    assert user.portal_role is None
    assert user.status == ACTIVE
    assert user.password_hash is None       # SSO-only, never a local password
    assert user.is_demo_account is False
    assert user.study_scope == "*"
    assert user.display_name == "Blessward Mutsotso"
    assert db.query(AuthAuditEvent).filter_by(
        event_type="SSO_USER_AUTO_PROVISIONED", affected_email=user.email
    ).count() == 1
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_does_not_duplicate_an_auto_provisioned_user(mock_sso_app):
    _set_sso_env()
    email = "repeat.signin@acrnhealth.com"
    _sso_callback(mock_sso_app, email)
    _sso_callback(mock_sso_app, email)

    db = TestingSession()
    assert db.query(PortalUser).filter_by(email=email).count() == 1
    assert db.query(AuthAuditEvent).filter_by(
        event_type="SSO_USER_AUTO_PROVISIONED", affected_email=email
    ).count() == 1
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_does_not_escalate_an_existing_account(mock_sso_app):
    """Auto-provisioning must never touch the role of someone who already has one."""
    _set_sso_env()
    db = TestingSession()
    db.add(PortalUser(
        email="existing.monitor@acrnhealth.com", display_name="Existing Monitor", password_hash=None,
        role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE, study_scope="PROTECT-Africa",
    ))
    db.commit()
    db.close()

    _sso_callback(mock_sso_app, "existing.monitor@acrnhealth.com")

    db = TestingSession()
    user = db.query(PortalUser).filter_by(email="existing.monitor@acrnhealth.com").one()
    assert user.role == "MONITOR"
    assert user.portal_role == "MONITOR_QC_REVIEWER"
    assert user.study_scope == "PROTECT-Africa"
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_rejects_deactivated_account_without_reactivating_it(mock_sso_app):
    _set_sso_env()
    db = TestingSession()
    db.add(PortalUser(
        email="deactivated@acrnhealth.com", display_name="Deactivated", password_hash=None,
        role="ADJUDICATOR", status="INACTIVE",
    ))
    db.commit()
    db.close()

    r = _sso_callback(mock_sso_app, "deactivated@acrnhealth.com")

    assert r.status_code in (302, 307)
    assert "sso_error=account_inactive" in r.headers["location"]
    assert "acrn_demo_session" not in r.cookies

    db = TestingSession()
    assert db.query(PortalUser).filter_by(email="deactivated@acrnhealth.com").one().status == "INACTIVE"
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_rejects_token_without_an_email_claim(mock_sso_app):
    _set_sso_env()
    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {"id_token_claims": {"name": "No Email"}}
    mock_sso_app.return_value = mock_client

    r = client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "sso_error=auth_failed" in r.headers["location"]
    assert "acrn_demo_session" not in r.cookies
