"""Login, logout and demo account management endpoints."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, INACTIVE, ROLE_ADMIN, audit_auth, current_user, default_password,
    hash_password, identity_from_user, login as auth_login, logout as auth_logout,
    require_role, seed_demo_accounts, normalize_email,
)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=3)


class StatusRequest(ReasonRequest):
    status: str


class RoleRequest(ReasonRequest):
    role: str


def public_user(user: PortalUser) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name,
        "role": user.role.title(),
        "roleCode": user.role,
        "portal": {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator"}[user.role],
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


@router.post("/users/{user_id}/status")
def set_status(user_id: str, req: StatusRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
               db: Session = Depends(get_db)):
    status = req.status.upper()
    if status not in {ACTIVE, INACTIVE}:
        raise HTTPException(422, "Unsupported account status")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    previous = row.status
    row.status = status
    audit_auth(db, "ACCOUNT_ACTIVATION" if status == ACTIVE else "ACCOUNT_DEACTIVATION", "SUCCESS",
               actor=admin, affected=row, request=request, reason=req.reason, details={"previous_status": previous, "status": status})
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/unlock")
def unlock(user_id: str, req: ReasonRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
           db: Session = Depends(get_db)):
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
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    if not row.is_demo_account:
        raise HTTPException(409, "Only demo account passwords can be reset here")
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
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR"}:
        raise HTTPException(422, "Unsupported role")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    previous = row.role
    row.role = role
    audit_auth(db, "ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason, details={"previous_role": previous, "role": role})
    db.commit()
    return public_user(row)


@router.get("/audit")
def audit(limit: int = Query(100, ge=1, le=500), admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
          db: Session = Depends(get_db)):
    rows = db.query(AuthAuditEvent).order_by(AuthAuditEvent.timestamp.desc()).limit(limit).all()
    return {"items": [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]}


@router.post("/demo/seed")
def seed(req: ReasonRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)), db: Session = Depends(get_db)):
    created = seed_demo_accounts(db)
    audit_auth(db, "DEMO_ACCOUNTS_SEEDED", "SUCCESS", actor=admin, affected=admin, request=request, reason=req.reason, details={"created": created})
    db.commit()
    return {"created": created}
