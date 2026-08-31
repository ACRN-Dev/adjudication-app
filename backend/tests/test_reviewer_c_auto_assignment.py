import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from models.auth import PortalUser
from models.canonical import (
    AdjudicationStatus,
    AdjudicationRecord,
    DiagnosisCode,
    OnsetClass,
    Participant,
    SeverityGrade,
    StudyCode,
    SubjectAssignment,
    CertaintyLevel,
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


def _seed_case(a_email, b_email):
    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]
    c_email = f"c-{suffix}@acrnhealth.com"
    d_email = f"d-{suffix}@acrnhealth.com"
    db.query(PortalUser).filter(PortalUser.email.in_([a_email, b_email])).delete(synchronize_session=False)
    users = []
    for email in [a_email, b_email, c_email, d_email]:
        users.append(PortalUser(
            email=email,
            display_name=email.split("@")[0],
            password_hash=hash_password("ACRN@2026"),
            role="ADJUDICATOR",
            status="ACTIVE",
            is_demo_account=True,
        ))
    db.add_all(users)
    participant = Participant(
        subject_id=f"AUTO-C-{suffix}",
        case_number=f"ADJ-AUTO-{suffix}",
        study=StudyCode.EOPE,
        status=AdjudicationStatus.IN_REVIEW,
        qc_approved=True,
    )
    db.add(participant)
    db.flush()
    db.add(SubjectAssignment(
        participant_id=participant.id,
        reviewer_a_upn=a_email,
        reviewer_b_upn=b_email,
        status="ACTIVE",
    ))
    db.commit()
    case_number = participant.case_number
    db.close()
    return case_number, {c_email, d_email}


def _submit(case_number, role, email, diagnosis, password="ACRN@2026", mfa_code=None):
    return client.post(f"/api/adjudication/{case_number}/submit", json={
        "reviewer_role": role,
        "reviewer_upn": email,
        "reviewer_name": email.split("@")[0],
        "reviewer_password": password,
        "mfa_code": mfa_code,
        "visit_number": 1,
        "meets_criteria": True,
        "diagnosis": diagnosis,
        "date_of_diagnosis": "2026-08-01T10:00:00",
        "onset_class": OnsetClass.EOPE.value,
        "severity": SeverityGrade.WITH_SEVERE.value,
        "certainty": CertaintyLevel.DEFINITE.value,
        "rationale": "Complete clinical rationale for endpoint classification.",
    })


def test_matching_reviewers_are_concordant_and_discordance_assigns_independent_reviewer_c():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        concordant_case, _ = _seed_case("a1@acrnhealth.com", "b1@acrnhealth.com")
        assert _submit(concordant_case, "REVIEWER_A", "a1@acrnhealth.com", DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        result = _submit(concordant_case, "REVIEWER_B", "b1@acrnhealth.com", DiagnosisCode.PREECLAMPSIA.value)
        assert result.status_code == 200
        assert result.json()["participant_status"] == AdjudicationStatus.CONCORDANT.value

        discordant_case, independent_reviewers = _seed_case("a2@acrnhealth.com", "b2@acrnhealth.com")
        assert _submit(discordant_case, "REVIEWER_A", "a2@acrnhealth.com", DiagnosisCode.PREECLAMPSIA.value).status_code == 200
        result = _submit(discordant_case, "REVIEWER_B", "b2@acrnhealth.com", DiagnosisCode.HELLP.value)
        assert result.status_code == 200
        assert result.json()["participant_status"] == AdjudicationStatus.COMMITTEE_PENDING.value

        db = TestingSession()
        participant = db.query(Participant).filter_by(case_number=discordant_case).one()
        assignment = db.query(SubjectAssignment).filter_by(participant_id=participant.id).one()
        assert assignment.reviewer_c_upn not in {"a2@acrnhealth.com", "b2@acrnhealth.com"}
        assert db.query(PortalUser).filter_by(email=assignment.reviewer_c_upn, role="ADJUDICATOR", status="ACTIVE").one()
        assert assignment.reviewer_c_upn not in {"a2@acrnhealth.com", "b2@acrnhealth.com"}
        db.close()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_demo_signature_step_up_otp_allows_workflow_when_password_was_reset(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        case_number, _ = _seed_case("otp-a@acrnhealth.com", "otp-b@acrnhealth.com")
        result = _submit(
            case_number,
            "REVIEWER_A",
            "otp-a@acrnhealth.com",
            DiagnosisCode.PREECLAMPSIA.value,
            password="not-the-current-password",
            mfa_code="849201",
        )
        assert result.status_code == 200
        assert result.json()["status"] == "success"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
