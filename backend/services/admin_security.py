"""Replaceable identity adapter and server-side Admin Portal authorization."""
import hashlib, json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, Depends, Request, Cookie
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import event
from models.admin import AdminAuditEvent
from models.auth import PortalUser

ROLE_PERMISSIONS = {
    "ADMIN": {"admin.read", "users.read", "users.manage", "roles.read", "studies.manage", "sites.manage", "rules.manage", "mappings.manage", "forms.manage", "workflows.manage", "integrations.manage", "audit.read", "reports.read", "access.approve", "access.review"},
    "TECHNICAL_ADMIN": {"admin.read", "users.read", "users.manage", "roles.read", "integrations.manage", "audit.read", "reports.read"},
    "CLINICAL_OPS_ADMIN": {"admin.read", "users.read", "studies.manage", "sites.manage", "rules.manage", "mappings.manage", "forms.manage", "workflows.manage", "audit.read", "reports.read", "access.approve"},
    "QA_AUDITOR": {"admin.read", "audit.read", "reports.read", "rules.approve", "mappings.approve", "forms.approve"},
    "GOVERNANCE_REVIEWER": {"admin.read", "roles.read", "studies.read", "rules.read", "audit.read", "reports.read"},
    "ACCESS_REVIEWER": {"admin.read", "users.read", "access.review", "audit.read", "reports.read"},
}
ADMIN_ROLES = set(ROLE_PERMISSIONS)
PROHIBITED_FIELDS = {"sflt1", "sflt-1", "plgf", "seng", "biomarkerresults", "biomarker_results", "pocresults", "poc_results", "treatmentallocation", "treatment_allocation"}
HIGH_RISK = [
    ({"TECHNICAL_ADMIN", "ADJUDICATOR"}, "Technical administrator plus adjudicator"),
    ({"MONITOR_QC", "ADJUDICATOR"}, "Monitor/QC plus independent adjudicator"),
    ({"ADJUDICATOR", "FINAL_RELEASE_APPROVER"}, "Reviewer plus final-release approver"),
    ({"USER_ADMIN", "SELF_ACCESS_APPROVER"}, "User administrator plus self-access approver"),
    ({"COMMITTEE_MEMBER", "SITE_OPERATIONS"}, "Committee member with incompatible operational access"),
]

@dataclass(frozen=True)
class Identity:
    upn: str; role: str; studies: tuple[str, ...]; auth_source: str = "DEMO"
    @property
    def permissions(self): return ROLE_PERMISSIONS.get(self.role, set())

def get_identity(request: Request, acrn_demo_session: Optional[str] = Cookie(None), db: Session = Depends(get_db), x_demo_user: Optional[str] = Header(None), x_demo_role: Optional[str] = Header(None), x_study_scope: Optional[str] = Header(None)):
    """Session adapter with legacy demo-header fallback for older local tests."""
    try:
        token = acrn_demo_session
        if token:
            from services.auth_service import _hash_token
            from models.auth import AuthSession
            session = db.query(AuthSession).filter_by(token_hash=_hash_token(token), revoked_at=None).first()
            if session and session.expires_at > datetime.utcnow():
                user = db.get(PortalUser, session.user_id)
                if user and user.status == "ACTIVE" and user.role in ADMIN_ROLES:
                    return Identity(user.email, user.role, tuple(filter(None, (x_study_scope or "*").split(","))))
                if user and user.status == "ACTIVE":
                    raise HTTPException(403, "Admin Portal access denied for this role.")
    except HTTPException:
        raise
    except Exception:
        pass
    if not x_demo_user or not x_demo_role:
        raise HTTPException(401, "Authentication required.")
    role = x_demo_role.upper()
    if role not in ADMIN_ROLES:
        raise HTTPException(403, "Admin Portal access denied for this role.")
    return Identity(x_demo_user, role, tuple(filter(None, (x_study_scope or "").split(","))))

def require(permission: str):
    def dependency(identity: Identity = Depends(get_identity)):
        if permission not in identity.permissions:
            raise HTTPException(403, f"Permission denied: {permission}")
        return identity
    return dependency

def enforce_study(identity: Identity, study_code: Optional[str]):
    if study_code and identity.studies and "*" not in identity.studies and study_code not in identity.studies:
        raise HTTPException(403, "Requested study is outside the administrator's delegated scope.")

def validate_delegation(identity: Identity, requested_permissions):
    excess = set(requested_permissions) - identity.permissions
    if excess: raise HTTPException(403, f"Cannot delegate permissions not held: {', '.join(sorted(excess))}")

def risk_warnings(role_codes):
    roles = set(role_codes)
    return [label for pair, label in HIGH_RISK if pair <= roles]

def canonical_field_key(value): return "".join(ch for ch in (value or "").lower() if ch.isalnum() or ch == "_")

def validate_mapping(definition):
    from services.clinical_import_policy import assert_not_adjudicator_outcome_mapping
    fields = [definition.get("source_field"), definition.get("canonical_field")]
    if any(canonical_field_key(f) in PROHIBITED_FIELDS for f in fields):
        raise HTTPException(422, "Prohibited blinded or unblinding field cannot be mapped to adjudicator-facing data.")
    assert_not_adjudicator_outcome_mapping(definition.get("source_field"), definition.get("canonical_field"))

def validate_workflow_definition(definition):
    states = definition.get("states", [])
    transitions = definition.get("transitions", [])
    for item in transitions:
        source, target = item.get("source"), item.get("target")
        if source not in states or target not in states or source == target:
            raise HTTPException(422, "Workflow contains an impossible transition.")
        if source == "Imported" and target in {"Assigned", "Reviewer In Progress", "Reviewer Submitted"}:
            raise HTTPException(422, "Direct movement from import to adjudication is prohibited.")
        if target == "Released" and source != "Ready for Release":
            raise HTTPException(422, "Release is allowed only from Ready for Release after Final QC.")
        if source in {"Committee Locked", "Released", "Archived"} and target not in {"Final QC", "Archived"}:
            raise HTTPException(422, "Locked records require the controlled-reopen process.")
    return True

def add_audit(db, identity, action, entity_type, entity_id, reason, previous=None, new=None, study_code=None, outcome="SUCCESS", is_demo=True):
    payload = {"t": datetime.now(timezone.utc).isoformat(), "a": identity.upn, "x": action, "e": entity_id, "n": new}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    row = AdminAuditEvent(actor_upn=identity.upn, actor_role=identity.role, action=action, entity_type=entity_type,
        entity_id=str(entity_id or ""), reason=reason, previous_value=previous, new_value=new, study_code=study_code,
        outcome=outcome, is_demo=is_demo, record_hash=digest)
    db.add(row); return row

@event.listens_for(AdminAuditEvent, "before_update")
def _no_audit_update(*_): raise ValueError("Audit events are immutable")
@event.listens_for(AdminAuditEvent, "before_delete")
def _no_audit_delete(*_): raise ValueError("Audit events are immutable")
