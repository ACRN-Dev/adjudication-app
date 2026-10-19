"""Qualification tests for access certification and retention/legal-hold controls."""
from datetime import datetime, timedelta
import hashlib
import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["ENABLE_DEMO_ACCOUNTS"] = "true"
os.environ["ENABLE_DEMO_DATA"] = "true"

from main import app
from conftest import TestingSession
from models.admin import AccessReview, AdminUser
from models.auth import PortalUser
from services.auth_service import ACTIVE, hash_password


client = TestClient(app)
ADMIN = {"X-Demo-User": "governance.admin@acrnhealth.com", "X-Demo-Role": "ADMIN", "X-Study-Scope": "*"}
QA = {"X-Demo-User": "independent.qa@acrnhealth.com", "X-Demo-Role": "QA_AUDITOR", "X-Study-Scope": "*"}
REVIEWER = {"X-Demo-User": "access.reviewer@acrnhealth.com", "X-Demo-Role": "ACCESS_REVIEWER", "X-Study-Scope": "*"}


def test_retention_policy_requires_independent_approval_and_legal_hold_blocks_disposition():
    created = client.post("/api/admin/retention/policies", headers=ADMIN, json={
        "record_type": "AUTH_SESSION", "retention_days": 30, "trigger_event": "SESSION_REVOKED",
        "legal_basis": "Approved information governance schedule", "reason": "Create controlled retention schedule",
    })
    assert created.status_code == 201
    policy_id = created.json()["id"]
    assert client.post(f"/api/admin/retention/policies/{policy_id}/activate", headers=ADMIN,
                       json={"reason": "Attempt self approval"}).status_code == 409
    activated = client.post(f"/api/admin/retention/policies/{policy_id}/activate", headers=QA,
                            json={"reason": "Independent QA policy approval"})
    assert activated.status_code == 200 and activated.json()["status"] == "ACTIVE"

    hold = client.post("/api/admin/retention/legal-holds", headers=ADMIN, json={
        "name": "Investigation hold", "scope_type": "STUDY", "scope_value": "PROTECT-Africa",
        "reason": "Preserve evidence during investigation",
    })
    assert hold.status_code == 201
    payload = {
        "record_type": "AUTH_SESSION", "record_reference": "session-123", "scope_value": "PROTECT-Africa",
        "record_created_at": (datetime.utcnow() - timedelta(days=31)).isoformat(),
        "reason": "Retention period elapsed and record is eligible",
    }
    assert client.post("/api/admin/retention/dispositions", headers=ADMIN, json=payload).status_code == 423
    assert client.post(f"/api/admin/retention/legal-holds/{hold.json()['id']}/release", headers=QA,
                       json={"reason": "Investigation formally closed"}).status_code == 200
    disposition = client.post("/api/admin/retention/dispositions", headers=ADMIN, json=payload)
    assert disposition.status_code == 201
    disposition_id = disposition.json()["id"]
    assert client.post(f"/api/admin/retention/dispositions/{disposition_id}/approve", headers=ADMIN,
                       json={"reason": "Attempt self approval"}).status_code == 409
    assert client.post(f"/api/admin/retention/dispositions/{disposition_id}/approve", headers=QA,
                       json={"reason": "Independent disposition approval"}).status_code == 200
    evidence_hash = hashlib.sha256(b"signed destruction certificate").hexdigest()
    executed = client.post(f"/api/admin/retention/dispositions/{disposition_id}/execute", headers=QA, json={
        "reason": "Record verified as destroyed by approved storage operator",
        "execution_reference": "CERT-2026-001", "evidence_sha256": evidence_hash,
    })
    assert executed.status_code == 200
    assert executed.json()["evidence"]["evidence_sha256"] == evidence_hash


def test_access_review_snapshot_is_complete_locked_and_applies_revocation():
    db = TestingSession()
    target = AdminUser(display_name="Review Target", email="review.target@example.test", country="Zimbabwe",
                       status="Active", is_demo=True)
    portal = PortalUser(email="review.target@example.test", display_name="Review Target",
                        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE)
    db.add_all([target, portal]); db.flush()
    snapshot = [{"user_id": target.id, "email": target.email, "status": target.status, "role_codes": [], "access_expiry": None}]
    review = AccessReview(name="Focused access certification", scope_type="USER", scope_value=target.email,
                          reviewer_upn=REVIEWER["X-Demo-User"], status="Open", due_at=datetime.utcnow()+timedelta(days=7),
                          snapshot=snapshot, snapshot_hash=hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
                          decisions=[], is_demo=True)
    db.add(review); db.commit(); review_id=review.id; target_id=target.id; db.close()

    decision = client.post(f"/api/admin/access-reviews/{review_id}/decisions", headers=REVIEWER, json={
        "user_id": target_id, "decision": "REVOKE", "reason": "Access no longer required for assigned duties",
    })
    assert decision.status_code == 200
    completed = client.post(f"/api/admin/access-reviews/{review_id}/complete", headers=REVIEWER, json={
        "reason": "All scoped access decisions independently certified",
        "certification": "I certify this review is complete, accurate, and supported by current role evidence.",
    })
    assert completed.status_code == 200 and completed.json()["locked"] is True
    assert client.post(f"/api/admin/access-reviews/{review_id}/decisions", headers=REVIEWER, json={
        "user_id": target_id, "decision": "RETAIN", "reason": "Attempt to alter locked review",
    }).status_code == 409
    db = TestingSession()
    assert db.get(AdminUser, target_id).status == "Deactivated"
    assert db.query(PortalUser).filter_by(email="review.target@example.test").one().status == "DEACTIVATED"
    db.close()


def test_record_specific_legal_hold_blocks_only_matching_record():
    policy = client.post("/api/admin/retention/policies", headers=ADMIN, json={
        "record_type": "SIGNED_ARTIFACT", "retention_days": 1,
        "legal_basis": "Approved essential-record retention schedule", "reason": "Create artifact schedule",
    })
    assert policy.status_code == 201
    assert client.post(f"/api/admin/retention/policies/{policy.json()['id']}/activate", headers=QA,
                       json={"reason": "Independent approval"}).status_code == 200
    hold = client.post("/api/admin/retention/legal-holds", headers=ADMIN, json={
        "name": "Single record hold", "scope_type": "RECORD", "scope_value": "artifact-held",
        "reason": "Preserve named record for investigation",
    })
    assert hold.status_code == 201
    common = {"record_type": "SIGNED_ARTIFACT", "scope_value": "PROTECT-Africa",
              "record_created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
              "reason": "Retention eligibility assessment"}
    blocked = client.post("/api/admin/retention/dispositions", headers=ADMIN,
                          json={**common, "record_reference": "artifact-held"})
    allowed = client.post("/api/admin/retention/dispositions", headers=ADMIN,
                          json={**common, "record_reference": "artifact-other"})
    assert blocked.status_code == 423
    assert allowed.status_code == 201
