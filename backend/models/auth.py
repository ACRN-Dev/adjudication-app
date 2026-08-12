"""Demo authentication domain for controlled prototype access."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from database import Base


def uid():
    return str(uuid.uuid4())


class PortalUser(Base):
    __tablename__ = "portal_users"
    id = Column(String(36), primary_key=True, default=uid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(160), nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(30), nullable=False, index=True)
    portal_role = Column(String(40), nullable=True)
    study_scope = Column(String(500), nullable=True, default="*")
    status = Column(String(30), nullable=False, default="ACTIVE", index=True)
    is_demo_account = Column(Boolean, nullable=False, default=True, index=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id = Column(String(36), primary_key=True, default=uid)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime)
    user_agent = Column(String(255))
    ip_address = Column(String(80))


class AuthAuditEvent(Base):
    __tablename__ = "auth_audit_events"
    id = Column(String(36), primary_key=True, default=uid)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    actor_user_id = Column(String(36))
    actor_email = Column(String(255))
    actor_role = Column(String(30))
    affected_user_id = Column(String(36))
    affected_email = Column(String(255))
    event_type = Column(String(80), nullable=False, index=True)
    outcome = Column(String(30), nullable=False, default="SUCCESS")
    request_metadata = Column(JSON, default=dict)
    details = Column(JSON, default=dict)
    reason = Column(Text)
