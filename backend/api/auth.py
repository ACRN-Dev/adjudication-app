"""Login, logout and demo account management endpoints."""
import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import msal

from database import get_db
from models.auth import CommitteeAssignment, PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, AUTH_COOKIE_SECURE, AUTH_COOKIE_SAMESITE, INACTIVE, ROLE_ADJUDICATOR, ROLE_ADMIN, audit_auth,
    current_user, default_password, hash_password, identity_from_user, issue_session,
    login as auth_login, logout as auth_logout, require_role, seed_demo_accounts, normalize_email,
)
from services.admin_security import ADMIN_ROLES, ROLE_PERMISSIONS, Identity as AdminIdentity, validate_delegation
from services.monitor_security import ROLES as MONITOR_ROLES

router = APIRouter()

SSO_STATE_COOKIE = "acrn_sso_state"
SSO_SCOPES = ["User.Read"]


def _sso_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=os.environ["ENTRA_CLIENT_ID"],
        client_credential=os.environ["ENTRA_CLIENT_SECRET"],
        authority=f"https://login.microsoftonline.com/{os.environ['ENTRA_TENANT_ID']}",
    )


def _sso_redirect_uri() -> str:
    return f"{os.environ['APP_BASE_URL'].rstrip('/')}/api/auth/sso/callback"


@router.get("/config")
def auth_config():
    configured = os.getenv("ENABLE_DEMO_ACCOUNTS")
    if configured is not None:
        return {"demo_enabled": configured.strip().lower() in {"true", "1", "yes"}}
    return {"demo_enabled": False}



@router.get("/sso/login")
def sso_login(request: Request, db: Session = Depends(get_db)):
    base = os.environ.get("APP_BASE_URL", "").rstrip("/")
    try:
        state = secrets.token_urlsafe(24)
        auth_url = _sso_app().get_authorization_request_url(SSO_SCOPES, state=state, redirect_uri=_sso_redirect_uri())
    except Exception as e:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason=f"SSO misconfigured: {e}")
        db.commit()
        return RedirectResponse(f"{base}/?sso_error=not_configured")
    resp = RedirectResponse(auth_url)
    resp.set_cookie(SSO_STATE_COOKIE, state, httponly=True, secure=AUTH_COOKIE_SECURE, samesite=AUTH_COOKIE_SAMESITE, max_age=600, path="/")
    return resp


@router.get("/sso/callback")
def sso_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None,
                  acrn_sso_state: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    base = os.environ.get("APP_BASE_URL", "").rstrip("/")

    def redirect(path: str) -> RedirectResponse:
        r = RedirectResponse(f"{base}{path}")
        r.delete_cookie(SSO_STATE_COOKIE, path="/")
        return r

    if error or not code:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason=error or "No authorization code returned")
        db.commit()
        return redirect("/?sso_error=cancelled")

    if not state or not acrn_sso_state or state != acrn_sso_state:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason="State mismatch")
        db.commit()
        raise HTTPException(400, "Invalid SSO state")

    result = _sso_app().acquire_token_by_authorization_code(code, scopes=SSO_SCOPES, redirect_uri=_sso_redirect_uri())
    if "error" in result:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason=result.get("error_description", "Token exchange failed"))
        db.commit()
        return redirect("/?sso_error=auth_failed")

    claims = result.get("id_token_claims", {})
    email = normalize_email(claims.get("preferred_username") or claims.get("email") or "")
    if not email:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request,
                   reason="Microsoft returned no email claim")
        db.commit()
        return redirect("/?sso_error=auth_failed")

    user = db.query(PortalUser).filter_by(email=email).first()
    event_type = "SSO_LOGIN_SUCCESS"

    if user is None:
        # WS7: Restrict access to accounts on the committee roster. Unregistered tenant accounts are rejected and logged.
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request,
                   reason="Tenant account is not registered on the adjudication roster",
                   details={"attempted_email": email})
        db.commit()
        return redirect("/?sso_error=not_registered")

    elif user.status != ACTIVE:
        # An account an admin deactivated must stay out; never silently reactivate it.
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", affected=user, request=request,
                   reason="Account is not active")
        db.commit()
        return redirect("/?sso_error=account_inactive")

    resp = redirect("/")
    issue_session(db, user, resp, request, event_type)
    return resp



class LoginRequest(BaseModel):
    email: str
    password: str


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=3)


class StatusRequest(ReasonRequest):
    status: str


class RoleRequest(ReasonRequest):
    role: str


class CreateUserRequest(ReasonRequest):
    email: str
    display_name: str
    role: str
    portal_role: Optional[str] = None
    study_scope: str = "*"
    password: Optional[str] = None


class PortalRoleRequest(ReasonRequest):
    portal_role: Optional[str] = None


class StudyScopeRequest(ReasonRequest):
    study_scope: str


class CommitteeAssignmentRequest(ReasonRequest):
    committee_name: Optional[str] = None
    expires_at: Optional[datetime] = None


def public_user(user: PortalUser) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name,
        "role": user.role.title(),
        "roleCode": user.role,
        "portal_role": user.portal_role,
        "study_scope": user.study_scope,
        "portal": {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator", "CHAIRPERSON": "chairperson"}.get(user.role, "adjudicator"),
        "status": user.status,
        "is_demo_account": user.is_demo_account,
        "demo": user.is_demo_account,
        "must_change_password": user.must_change_password,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.post("/login")
def login(req: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    return auth_login(db, req.email, req.password, response, request)


@router.post("/logout")
def logout(response: Response, request: Request, token: Optional[str] = Cookie(None, alias=AUTH_COOKIE),
           db: Session = Depends(get_db), user: PortalUser = Depends(current_user)):
    auth_logout(db, token, response, request, user)
    return {"ok": True}


@router.get("/me")
def me(user: PortalUser = Depends(current_user)):
    return public_user(user)


@router.get("/users")
def users(search: str = "", role: str = "", status: str = "", page: int = Query(1, ge=1),
          page_size: int = Query(50, ge=1, le=200), admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
          db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.read")
    q = db.query(PortalUser)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter((PortalUser.email.ilike(s)) | (PortalUser.display_name.ilike(s)))
    if role:
        q = q.filter(PortalUser.role == role.upper())
    if status:
        q = q.filter(PortalUser.status == status.upper())
    total = q.count()
    rows = q.order_by(PortalUser.display_name).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [public_user(x) for x in rows]}


@router.get("/committee-assignments")
def committee_assignments(admin: PortalUser = Depends(require_role(ROLE_ADMIN)), db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    rows = db.query(CommitteeAssignment).order_by(CommitteeAssignment.assigned_at.desc()).all()
    users_by_id = {u.id: u for u in db.query(PortalUser).filter(PortalUser.id.in_([r.user_id for r in rows])).all()} if rows else {}
    return {
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "email": users_by_id[row.user_id].email if row.user_id in users_by_id else None,
                "display_name": users_by_id[row.user_id].display_name if row.user_id in users_by_id else None,
                "assignment_type": row.assignment_type,
                "committee_name": row.committee_name,
                "is_active": row.is_active,
                "status": row.status,
                "assigned_by": row.assigned_by,
                "assigned_at": row.assigned_at,
                "expires_at": row.expires_at,
            }
            for row in rows
        ]
    }


@router.post("/users/{user_id}/committee-assignment", status_code=201)
def assign_committee_chair(user_id: str, req: CommitteeAssignmentRequest, request: Request,
                           admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                           db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    target = db.get(PortalUser, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.role != "CHAIRPERSON":
        raise HTTPException(422, "Committee chair assignments can only be given to CHAIRPERSON users")
    if target.status != ACTIVE:
        raise HTTPException(409, "Cannot assign an inactive user")

    row = CommitteeAssignment(
        user_id=target.id,
        assignment_type="CHAIRPERSON",
        committee_name=req.committee_name,
        is_active=True,
        assigned_by=admin.id,
        expires_at=req.expires_at,
        status=ACTIVE,
        assignment_metadata={"reason": req.reason},
    )
    db.add(row)
    db.flush()
    audit_auth(db, "CHAIRPERSON_ASSIGNMENT_CREATED", actor=admin, affected=target, request=request,
               reason=req.reason, details={"assignment_id": row.id, "committee_name": req.committee_name,
                                           "expires_at": req.expires_at.isoformat() if req.expires_at else None})
    db.commit()
    return {"id": row.id, "user_id": row.user_id, "status": row.status, "is_active": row.is_active}


@router.post("/committee-assignments/{assignment_id}/deactivate")
def deactivate_committee_assignment(assignment_id: str, req: ReasonRequest, request: Request,
                                    admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                                    db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    row = db.get(CommitteeAssignment, assignment_id)
    if not row:
        raise HTTPException(404, "Committee assignment not found")
    if not row.is_active or row.status != ACTIVE:
        raise HTTPException(409, "Committee assignment is already inactive")
    row.is_active = False
    row.status = INACTIVE
    audit_auth(db, "CHAIRPERSON_ASSIGNMENT_DEACTIVATED", actor=admin, request=request,
               reason=req.reason, details={"assignment_id": row.id, "user_id": row.user_id})
    db.commit()
    return {"id": row.id, "status": row.status, "is_active": row.is_active}


def _require_admin_permission(admin: PortalUser, permission: str) -> AdminIdentity:
    acting_identity = AdminIdentity(admin.email, admin.portal_role or "", ())
    if permission not in acting_identity.permissions:
        raise HTTPException(403, f"Your admin role does not have '{permission}' permission.")
    return acting_identity


@router.post("/users/{user_id}/status")
def set_status(user_id: str, req: StatusRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
               db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    status = req.status.upper()
    if status not in {ACTIVE, INACTIVE}:
        raise HTTPException(422, "Unsupported account status")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if row.id == admin.id:
        raise HTTPException(409, "You cannot change your own account status.")
    previous = row.status
    row.status = status
    audit_auth(db, "ACCOUNT_ACTIVATION" if status == ACTIVE else "ACCOUNT_DEACTIVATION", "SUCCESS",
               actor=admin, affected=row, request=request, reason=req.reason, details={"previous_status": previous, "status": status})
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/unlock")
def unlock(user_id: str, req: ReasonRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
           db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    row.locked_until = None
    row.failed_login_count = 0
    audit_auth(db, "ACCOUNT_UNLOCK", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason)
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, req: ReasonRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                   db: Session = Depends(get_db)):
    acting_identity = _require_admin_permission(admin, "users.manage")
    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() != "true":
        raise HTTPException(409, "Demo accounts are disabled in this environment.")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if not row.is_demo_account:
        raise HTTPException(409, "Only demo account passwords can be reset here")
    if row.role == "ADMIN":
        validate_delegation(acting_identity, ROLE_PERMISSIONS.get(row.portal_role, set()))
    row.password_hash = hash_password(default_password())
    row.must_change_password = False
    row.failed_login_count = 0
    row.locked_until = None
    audit_auth(db, "PASSWORD_RESET", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason)
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/role")
def set_role(user_id: str, req: RoleRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
             db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR", "CHAIRPERSON"}:
        raise HTTPException(422, "Unsupported role")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if row.id == admin.id:
        raise HTTPException(409, "You cannot change your own role.")
    previous = row.role
    previous_portal_role = row.portal_role
    row.role = role
    if role == "MONITOR":
        row.portal_role = "MONITOR_QC_REVIEWER"
    elif role == "ADMIN":
        row.portal_role = "ADMIN"
    else:
        row.portal_role = None
    audit_auth(db, "ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"previous_role": previous, "role": role, "previous_portal_role": previous_portal_role, "portal_role": row.portal_role})
    db.commit()
    return public_user(row)


def _validate_portal_role(role: str, portal_role: Optional[str]):
    if role == "ADMIN" and portal_role not in ADMIN_ROLES:
        raise HTTPException(422, f"portal_role must be one of: {', '.join(sorted(ADMIN_ROLES))}")
    if role == "MONITOR" and portal_role not in MONITOR_ROLES:
        raise HTTPException(422, f"portal_role must be one of: {', '.join(sorted(MONITOR_ROLES))}")


def _normalize_study_scope(value: str) -> str:
    value = (value or "").strip()
    if value == "*":
        return "*"
    codes = [c.strip() for c in value.split(",") if c.strip()]
    if not codes:
        raise HTTPException(422, "study_scope must be '*' or a non-empty comma-separated list of study codes")
    return ",".join(codes)


@router.post("/users", status_code=201)
def create_user(req: CreateUserRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                 db: Session = Depends(get_db)):
    acting_identity = _require_admin_permission(admin, "users.manage")
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR", "CHAIRPERSON"}:
        raise HTTPException(422, "Unsupported role")
    normalized = normalize_email(req.email)
    if db.query(PortalUser).filter_by(email=normalized).first():
        raise HTTPException(409, "A user with this email already exists")
    portal_role = (req.portal_role or "").upper() or None
    if not portal_role:
        if role == "MONITOR":
            portal_role = "MONITOR_QC_REVIEWER"
        elif role == "ADMIN":
            portal_role = "ADMIN"
    _validate_portal_role(role, portal_role)
    if role == "ADMIN":
        validate_delegation(acting_identity, ROLE_PERMISSIONS.get(portal_role, set()))
    default_password = req.password or "ACRN@2026"
    password_hash = hash_password(default_password)
    row = PortalUser(
        email=normalized,
        display_name=req.display_name,
        password_hash=password_hash,
        role=role,
        portal_role=portal_role,
        study_scope=_normalize_study_scope(req.study_scope),
        status=ACTIVE,
        is_demo_account=False,
    )
    db.add(row)
    audit_auth(db, "USER_CREATED", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"role": role, "portal_role": portal_role})
    db.commit()
    return {**public_user(row), "default_password": default_password}



@router.post("/users/{user_id}/portal-role")
def set_portal_role(user_id: str, req: PortalRoleRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                     db: Session = Depends(get_db)):
    acting_identity = _require_admin_permission(admin, "users.manage")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if row.id == admin.id:
        raise HTTPException(409, "You cannot change your own portal role.")
    portal_role = (req.portal_role or "").upper() or None
    _validate_portal_role(row.role, portal_role)
    if row.role == "ADMIN":
        validate_delegation(acting_identity, ROLE_PERMISSIONS.get(portal_role, set()))
    previous = row.portal_role
    row.portal_role = portal_role
    audit_auth(db, "PORTAL_ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"previous_portal_role": previous, "portal_role": portal_role})
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/study-scope")
def set_study_scope(user_id: str, req: StudyScopeRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                     db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if row.id == admin.id:
        raise HTTPException(409, "You cannot change your own study scope.")
    normalized_scope = _normalize_study_scope(req.study_scope)
    previous = row.study_scope
    row.study_scope = normalized_scope
    audit_auth(db, "STUDY_SCOPE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"previous_study_scope": previous, "study_scope": normalized_scope})
    db.commit()
    return public_user(row)


@router.get("/audit")
def audit(limit: int = Query(100, ge=1, le=500), admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
          db: Session = Depends(get_db)):
    _require_admin_permission(admin, "audit.read")
    rows = db.query(AuthAuditEvent).order_by(AuthAuditEvent.timestamp.desc()).limit(limit).all()
    return {"items": [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]}


@router.post("/demo/seed")
def seed(req: ReasonRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)), db: Session = Depends(get_db)):
    _require_admin_permission(admin, "users.manage")
    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() != "true":
        raise HTTPException(409, "Demo accounts are disabled in this environment.")
    created = seed_demo_accounts(db)
    audit_auth(db, "DEMO_ACCOUNTS_SEEDED", "SUCCESS", actor=admin, affected=admin, request=request, reason=req.reason, details={"created": created})
    db.commit()
    return {"created": created}
