"""Password, session, demo-account seed and role authorization helpers."""
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database import get_db
from models.auth import AuthAuditEvent, AuthSession, CommitteeAssignment, PortalUser

ROLE_ADMIN = "ADMIN"
ROLE_MONITOR = "MONITOR"
ROLE_ADJUDICATOR = "ADJUDICATOR"
ROLE_CHAIRPERSON = "CHAIRPERSON"
ROLES = {ROLE_ADMIN, ROLE_MONITOR, ROLE_ADJUDICATOR, ROLE_CHAIRPERSON}
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
AUTH_COOKIE = "acrn_demo_session"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "12"))
LOCK_AFTER = int(os.getenv("LOGIN_LOCK_AFTER", "5"))
LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
DEFAULT_PASSWORD_ENV = "DEMO_DEFAULT_PASSWORD"
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE") or ("none" if AUTH_COOKIE_SECURE else "lax")

DEMO_ACCOUNTS = [
    ("admin@acrnhealth.com", "ACRN Demo Administrator", ROLE_ADMIN, "ADMIN"),
    ("chairperson@acrnhealth.com", "ACRN Demo Chairperson", ROLE_CHAIRPERSON, None),
    ("monitor1@acrnhealth.com", "ACRN Demo Monitor 1", ROLE_MONITOR, "MONITOR_QC_REVIEWER"),
    ("monitor2@acrnhealth.com", "ACRN Demo Monitor 2", ROLE_MONITOR, "QA_REVIEWER"),
    ("adjudicatora@acrnhealth.com", "ACRN Demo Adjudicator A", ROLE_ADJUDICATOR, None),
    ("adjudicatorb@acrnhealth.com", "ACRN Demo Adjudicator B", ROLE_ADJUDICATOR, None),
    ("adjudicatorc@acrnhealth.com", "ACRN Demo Adjudicator C", ROLE_ADJUDICATOR, None),
    ("adjudicatord@acrnhealth.com", "ACRN Demo Adjudicator D", ROLE_ADJUDICATOR, None),
]


@dataclass(frozen=True)
class AuthIdentity:
    id: str
    email: str
    display_name: str
    role: str
    is_demo_account: bool = True

    @property
    def portal(self) -> str:
        return {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator", "CHAIRPERSON": "chairperson"}.get(self.role, "adjudicator")



def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def default_password() -> str:
    return os.getenv(DEFAULT_PASSWORD_ENV, "ACRN@2026")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request_meta(request: Optional[Request]) -> dict:
    if not request:
        return {}
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
        "path": request.url.path,
    }


def audit_auth(db: Session, event_type: str, outcome: str = "SUCCESS", actor: Optional[PortalUser] = None,
               affected: Optional[PortalUser] = None, request: Optional[Request] = None, reason: str = "",
               details: Optional[dict] = None):
    db.add(AuthAuditEvent(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        actor_role=actor.role if actor else None,
        affected_user_id=affected.id if affected else None,
        affected_email=affected.email if affected else None,
        event_type=event_type,
        outcome=outcome,
        request_metadata=request_meta(request),
        details=details or {},
        reason=reason,
    ))


def seed_demo_accounts(db: Session, force_password_reset: bool = False) -> int:
    must_change = os.getenv("DEMO_FORCE_PASSWORD_CHANGE", "false").lower() == "true"
    created = 0
    for email, display_name, role, portal_role in DEMO_ACCOUNTS:
        normalized = normalize_email(email)
        row = db.query(PortalUser).filter_by(email=normalized).first()
        if not row:
            row = PortalUser(
                email=normalized,
                display_name=display_name,
                password_hash=hash_password(default_password()),
                role=role,
                portal_role=portal_role,
                status=ACTIVE,
                is_demo_account=True,
                must_change_password=must_change,
            )
            db.add(row)
            created += 1
        else:
            row.display_name = display_name
            row.role = role
            row.portal_role = portal_role
            row.status = row.status or ACTIVE
            row.is_demo_account = True
            if force_password_reset:
                row.password_hash = hash_password(default_password())
                row.must_change_password = must_change
                row.failed_login_count = 0
                row.locked_until = None

    chair_user = db.query(PortalUser).filter_by(email=normalize_email("chairperson@acrnhealth.com")).first()
    if chair_user and chair_user.role == ROLE_CHAIRPERSON:
        existing_assignment = (
            db.query(CommitteeAssignment)
            .filter_by(user_id=chair_user.id, assignment_type="CHAIRPERSON", status=ACTIVE)
            .filter(CommitteeAssignment.is_active.is_(True))
            .first()
        )
        if not existing_assignment:
            db.add(CommitteeAssignment(
                user_id=chair_user.id,
                assignment_type="CHAIRPERSON",
                committee_name="PROTECT-Africa Committee",
                is_active=True,
                status=ACTIVE,
                assignment_metadata={"source": "demo_seed"},
            ))
    db.commit()
    return created


def maybe_seed_demo_accounts(db: Session):
    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true":
        if os.getenv("SEED_DEMO_ACCOUNTS", "true").lower() == "true":
            seed_demo_accounts(db)


def _public_user(user: PortalUser) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name,
        "role": user.role.title(),
        "roleCode": user.role,
        "portal": {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator", "CHAIRPERSON": "chairperson"}.get(user.role, "adjudicator"),
        "status": user.status,
        "is_demo_account": user.is_demo_account,
        "demo": user.is_demo_account,
        "must_change_password": user.must_change_password,
        "last_login_at": user.last_login_at,
    }


def issue_session(db: Session, user: PortalUser, response: Response, request: Optional[Request], event_type: str = "LOGIN_SUCCESS") -> dict:
    now = datetime.utcnow()
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    raw_token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=_hash_token(raw_token),
        user_id=user.id,
        expires_at=now + timedelta(hours=SESSION_HOURS),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else ""),
        ip_address=(request.client.host if request and request.client else ""),
    ))
    audit_auth(db, event_type, "SUCCESS", actor=user, affected=user, request=request)
    db.commit()
    response.set_cookie(
        AUTH_COOKIE,
        raw_token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=SESSION_HOURS * 3600,
        path="/",
    )
    return _public_user(user)


def login(db: Session, email: str, password: str, response: Response, request: Request) -> dict:
    normalized = normalize_email(email)
    generic = HTTPException(401, "Invalid email or password.")
    user = db.query(PortalUser).filter_by(email=normalized).first()
    now = datetime.utcnow()
    if not user:
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", request=request, details={"email_hash": hashlib.sha256(normalized.encode()).hexdigest()})
        db.commit()
        raise generic
    if user.status != ACTIVE or (user.locked_until and user.locked_until > now):
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request, reason="Account inactive or locked")
        db.commit()
        raise generic
    if not user.password_hash or not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= LOCK_AFTER:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            audit_auth(db, "ACCOUNT_LOCK", "SUCCESS", affected=user, request=request, reason="Repeated failed login attempts")
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request)
        db.commit()
        raise generic
    return issue_session(db, user, response, request, "LOGIN_SUCCESS")


def logout(db: Session, token: Optional[str], response: Response, request: Request, user: Optional[PortalUser] = None):
    if token:
        session = db.query(AuthSession).filter_by(token_hash=_hash_token(token), revoked_at=None).first()
        if session:
            session.revoked_at = datetime.utcnow()
    audit_auth(db, "LOGOUT", "SUCCESS", actor=user, affected=user, request=request)
    db.commit()
    response.delete_cookie(AUTH_COOKIE, path="/", secure=AUTH_COOKIE_SECURE, samesite=AUTH_COOKIE_SAMESITE)


def current_user(acrn_demo_session: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> PortalUser:
    if not acrn_demo_session:
        raise HTTPException(401, "Authentication required")
    session = db.query(AuthSession).filter_by(token_hash=_hash_token(acrn_demo_session), revoked_at=None).first()
    if not session or session.expires_at <= datetime.utcnow():
        raise HTTPException(401, "Authentication required")
    user = db.get(PortalUser, session.user_id)
    if not user or user.status != ACTIVE or (user.locked_until and user.locked_until > datetime.utcnow()):
        raise HTTPException(401, "Authentication required")
    return user


def identity(user: PortalUser = Depends(current_user)) -> AuthIdentity:
    return AuthIdentity(user.id, user.email, user.display_name, user.role, user.is_demo_account)


def require_role(*roles: str):
    allowed = {r.upper() for r in roles}

    def dep(user: PortalUser = Depends(current_user), db: Session = Depends(get_db), request: Request = None):
        if user.role not in allowed:
            audit_auth(db, "UNAUTHORIZED_ACCESS_ATTEMPT", "FAILURE", actor=user, affected=user, request=request, details={"required": sorted(allowed)})
            db.commit()
            raise HTTPException(403, "Access denied")
        return user
    return dep


def has_active_committee_assignment(user: PortalUser, db: Session, assignment_type: str = "CHAIRPERSON") -> bool:
    if user.role != ROLE_CHAIRPERSON:
        return True

    now = datetime.utcnow()
    assignment = (
        db.query(CommitteeAssignment)
        .filter_by(user_id=user.id, assignment_type=assignment_type.upper(), status=ACTIVE)
        .filter(CommitteeAssignment.is_active.is_(True))
        .order_by(CommitteeAssignment.assigned_at.desc())
        .first()
    )

    if not assignment:
        return False
    if assignment.expires_at and assignment.expires_at <= now:
        return False
    return True


def require_chairperson_assignment():
    def dep(user: PortalUser = Depends(current_user), db: Session = Depends(get_db), request: Request = None):
        if user.role != ROLE_CHAIRPERSON:
            return user
        if not has_active_committee_assignment(user, db):
            audit_auth(
                db,
                "CHAIRPERSON_ASSIGNMENT_DENIED",
                "FAILURE",
                actor=user,
                affected=user,
                request=request,
                reason="No active committee chair assignment",
                details={"required_assignment": "CHAIRPERSON"},
            )
            db.commit()
            raise HTTPException(403, "Access denied: no active committee assignment for chairperson role")
        return user

    return dep


def identity_from_user(user: PortalUser) -> AuthIdentity:
    return AuthIdentity(user.id, user.email, user.display_name, user.role, user.is_demo_account)


def header_or_session_identity(x_demo_user: Optional[str] = Header(None), x_demo_role: Optional[str] = Header(None),
                               user: Optional[PortalUser] = Depends(current_user)):
    return identity_from_user(user)
