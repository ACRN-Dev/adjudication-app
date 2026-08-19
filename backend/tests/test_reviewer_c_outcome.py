"""
Test: Reviewer C outcome resolution — THREE_WAY_DIVERGENT and CONCORDANT_VIA_REVIEWER_C.

Verifies that after Reviewer C submits:
  1. If C agrees with A (or B) → participant becomes CONCORDANT
  2. If all three diverge    → participant becomes THREE_WAY_DIVERGENT
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from models.auth import PortalUser
from models.canonical import (
    AdjudicationStatus, DiagnosisCode, OnsetClass, Participant,
    SeverityGrade, StudyCode, SubjectAssignment, CertaintyLevel,
)
from services.auth_service import hash_password
from conftest import TestingSession
from database import get_db
from main import app


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)
_PASSWORD = "ACRN@2026"


def _make_users(db, *emails):
    for email in emails:
        db.query(PortalUser).filter_by(email=email).delete()
        db.add(PortalUser(
            email=email,
            display_name=email.split("@")[0],
            password_hash=hash_password(_PASSWORD),
            role="ADJUDICATOR",
            status="ACTIVE",
            is_demo_account=True,
        ))


def _seed_case(a_email, b_email, c_email):
    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]
    _make_users(db, a_email, b_email, c_email)
    p = Participant(
        subject_id=f"OUTCOME-{suffix}",
        case_number=f"ADJ-OUTCOME-{suffix}",
        study=StudyCode.EOPE,
        status=AdjudicationStatus.IN_REVIEW,
        qc_approved=True,
    )
    db.add(p)
    db.flush()
    db.add(SubjectAssignment(
        participant_id=p.id,
        reviewer_a_upn=a_email,
        reviewer_b_upn=b_email,
        reviewer_c_upn=c_email,
        status="ACTIVE",
        assigned_by="TEST_SEED",
    ))
    db.commit()
    case_number = p.case_number
    db.close()
    return case_number


def _submit(case_number, role, email, diagnosis, onset=OnsetClass.EOPE.value):
    return client.post(f"/api/adjudication/{case_number}/submit", json={
        "reviewer_role": role,
        "reviewer_upn": email,
        "reviewer_name": email.split("@")[0],
        "reviewer_password": _PASSWORD,
        "visit_number": 1,
        "meets_criteria": True,
        "diagnosis": diagnosis,
        "date_of_diagnosis": "2026-07-15T08:00:00",
        "onset_class": onset,
        "severity": SeverityGrade.WITH_SEVERE.value,
        "certainty": CertaintyLevel.DEFINITE.value,
        "rationale": "Full independent reviewer adjudication rationale.",
    })


def test_reviewer_c_agrees_with_a_produces_resolved_by_majority():
    """A=PE, B=NOT_PE, C=PE → C agrees with A → RESOLVED_BY_MAJORITY (prevents concordant rate inflation)"""
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        sfx = uuid.uuid4().hex[:6]
        a = f"oc-a-{sfx}@acrnhealth.com"
        b = f"oc-b-{sfx}@acrnhealth.com"
        c = f"oc-c-{sfx}@acrnhealth.com"
        case = _seed_case(a, b, c)

        assert _submit(case, "REVIEWER_A", a, DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        assert _submit(case, "REVIEWER_B", b, DiagnosisCode.NOT_PE.value).status_code == 200
        result = _submit(case, "REVIEWER_C", c, DiagnosisCode.PREECLAMPSIA.value)
        assert result.status_code == 200, result.text
        assert result.json()["participant_status"] == AdjudicationStatus.RESOLVED_BY_MAJORITY.value, \
            f"Expected RESOLVED_BY_MAJORITY, got: {result.json()['participant_status']}"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_all_three_diverge_produces_three_way_divergent():
    """A=PE, B=NOT_PE, C=GH (gestational hypertension mapped to separate code) → THREE_WAY_DIVERGENT
    Note: uses distinct DiagnosisCode values for all three.
    """
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        sfx = uuid.uuid4().hex[:6]
        a = f"twd-a-{sfx}@acrnhealth.com"
        b = f"twd-b-{sfx}@acrnhealth.com"
        c = f"twd-c-{sfx}@acrnhealth.com"
        case = _seed_case(a, b, c)

        assert _submit(case, "REVIEWER_A", a, DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        assert _submit(case, "REVIEWER_B", b, DiagnosisCode.NOT_PE.value).status_code == 200

        # C submits Gestational HTN — distinct from both A (PE) and B (Not PE) → three-way divergent
        result = _submit(case, "REVIEWER_C", c, DiagnosisCode.GESTATIONAL_HTN.value)
        assert result.status_code == 200, result.text
        assert result.json()["participant_status"] == AdjudicationStatus.THREE_WAY_DIVERGENT.value, \
            f"Expected THREE_WAY_DIVERGENT, got: {result.json()['participant_status']}"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_all_three_agree_produces_concordant():
    """A=PE, B=PE (but we force an initial discordance scenario for setup), C=PE → CONCORDANT"""
    # This tests the case where we manually pre-assign C but everyone submits the same diagnosis
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        sfx = uuid.uuid4().hex[:6]
        a = f"agree3-a-{sfx}@acrnhealth.com"
        b = f"agree3-b-{sfx}@acrnhealth.com"
        c = f"agree3-c-{sfx}@acrnhealth.com"
        case = _seed_case(a, b, c)

        # Submitting with A, B, and C all agreeing
        assert _submit(case, "REVIEWER_A", a, DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        assert _submit(case, "REVIEWER_B", b, DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        result = _submit(case, "REVIEWER_C", c, DiagnosisCode.PREECLAMPSIA.value)
        assert result.status_code == 200, result.text
        # All three agree → CONCORDANT
        assert result.json()["participant_status"] == AdjudicationStatus.CONCORDANT.value
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
