from datetime import datetime, timedelta
import uuid

from fastapi import Response

from conftest import TestingSession
from models.auth import AuthSession, PortalUser
from services import auth_service


def _user(db, prefix="session"):
    user = PortalUser(
        email=f"{prefix}-{uuid.uuid4().hex[:8]}@acrnhealth.com",
        display_name="Session Test User",
        role="ADJUDICATOR",
        status="ACTIVE",
        is_demo_account=False,
    )
    db.add(user)
    db.flush()
    return user


def test_issued_session_uses_idle_timeout_bounded_by_absolute_lifetime(monkeypatch):
    monkeypatch.setattr(auth_service, "SESSION_HOURS", 12)
    monkeypatch.setattr(auth_service, "SESSION_IDLE_MINUTES", 30)
    db = TestingSession()
    user = _user(db, "issued")
    response = Response()
    auth_service.issue_session(db, user, response, None)
    session = db.query(AuthSession).filter_by(user_id=user.id, revoked_at=None).one()
    lifetime = session.expires_at - session.created_at
    assert timedelta(minutes=29) <= lifetime <= timedelta(minutes=31)
    assert "HttpOnly" in response.headers["set-cookie"]
    db.close()


def test_idle_expired_session_is_revoked(monkeypatch):
    monkeypatch.setattr(auth_service, "SESSION_HOURS", 12)
    db = TestingSession()
    user = _user(db, "idle")
    session = AuthSession(
        token_hash=auth_service._hash_token("idle-token"), user_id=user.id,
        created_at=datetime.utcnow() - timedelta(hours=1),
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    db.add(session)
    db.commit()
    assert auth_service.resolve_session(db, "idle-token") is None
    assert session.revoked_at is not None
    db.close()


def test_absolute_lifetime_cannot_be_extended_by_activity(monkeypatch):
    monkeypatch.setattr(auth_service, "SESSION_HOURS", 12)
    monkeypatch.setattr(auth_service, "SESSION_IDLE_MINUTES", 30)
    db = TestingSession()
    user = _user(db, "absolute")
    session = AuthSession(
        token_hash=auth_service._hash_token("absolute-token"), user_id=user.id,
        created_at=datetime.utcnow() - timedelta(hours=13),
        expires_at=datetime.utcnow() + timedelta(minutes=20),
    )
    db.add(session)
    db.commit()
    assert auth_service.resolve_session(db, "absolute-token") is None
    assert session.revoked_at is not None
    db.close()


def test_privilege_change_helper_revokes_all_active_sessions():
    db = TestingSession()
    user = _user(db, "revoke")
    for index in range(2):
        db.add(AuthSession(
            token_hash=auth_service._hash_token(f"revoke-token-{index}"),
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        ))
    db.commit()
    assert auth_service.revoke_user_sessions(db, user.id) == 2
    db.commit()
    assert db.query(AuthSession).filter_by(user_id=user.id, revoked_at=None).count() == 0
    db.close()
