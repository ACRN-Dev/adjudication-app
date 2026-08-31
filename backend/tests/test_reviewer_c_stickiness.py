"""
Test: Reviewer C stickiness enforcement.
Verifies that:
  - Only the assigned Reviewer C can submit as REVIEWER_C.
  - An unassigned adjudicator receives 403 when submitting as REVIEWER_C.
  - An adjudicator submitting as REVIEWER_C before any assignment is created receives 409.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from models.auth import PortalUser
from models.canonical import (
    AdjudicationStatus, AdjudicationVisit, AdjudicationRecord, DiagnosisCode, OnsetClass,
    Participant, SeverityGrade, StudyCode, SubjectAssignment, CertaintyLevel,
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


def _seed_discordant_case_with_reviewer_c(a_email, b_email, c_email):
    """Seed a case that already has A, B (discordant), and a Reviewer C assignment."""
    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]

    # Create users
    for email in [a_email, b_email, c_email]:
        db.query(PortalUser).filter_by(email=email).delete()
        db.add(PortalUser(
            email=email,
            display_name=email.split("@")[0],
            password_hash=hash_password(_PASSWORD),
            role="ADJUDICATOR",
            status="ACTIVE",
            is_demo_account=True,
        ))

    participant = Participant(
        subject_id=f"STICKY-C-{suffix}",
        case_number=f"ADJ-STICKY-{suffix}",
        study=StudyCode.EOPE,
        status=AdjudicationStatus.COMMITTEE_PENDING,
        qc_approved=True,
    )
    db.add(participant)
    db.flush()
    visit = AdjudicationVisit(
        participant_id=participant.id,
        visit_number=1,
        visit_code="VISIT-1",
        status="AWAITING_REVIEWER_C",
        resolution_type="A_B_DISCORDANT",
    )
    db.add(visit)
    db.flush()

    # Add signed A and B records (discordant)
    db.add(AdjudicationRecord(
        participant_id=participant.id, visit_id=visit.id, visit_number=1,
        reviewer_role="REVIEWER_A",
        reviewer_upn=a_email, reviewer_name="Rev A",
        diagnosis=DiagnosisCode.PREECLAMPSIA, onset_class=OnsetClass.EOPE,
        severity=SeverityGrade.WITH_SEVERE, certainty=CertaintyLevel.DEFINITE,
        meets_criteria=True, rationale="Criteria met for PE.", signed=True,
    ))
    db.add(AdjudicationRecord(
        participant_id=participant.id, visit_id=visit.id, visit_number=1,
        reviewer_role="REVIEWER_B",
        reviewer_upn=b_email, reviewer_name="Rev B",
        diagnosis=DiagnosisCode.HELLP, onset_class=OnsetClass.EOPE,
        severity=SeverityGrade.WITH_SEVERE, certainty=CertaintyLevel.PROBABLE,
        meets_criteria=True, rationale="HELLP criteria supported by the visit evidence.", signed=True,
    ))

    # Assign Reviewer C explicitly
    db.add(SubjectAssignment(
        participant_id=participant.id,
        reviewer_a_upn=a_email,
        reviewer_b_upn=b_email,
        reviewer_c_upn=c_email,
        status="ACTIVE",
    ))

    db.commit()
    case_number = participant.case_number
    db.close()
    return case_number


def _submit_c(case_number, email, diagnosis=DiagnosisCode.PREECLAMPSIA.value):
    return client.post(f"/api/adjudication/{case_number}/submit", json={
        "reviewer_role": "REVIEWER_C",
        "reviewer_upn": email,
        "reviewer_name": email.split("@")[0],
        "reviewer_password": _PASSWORD,
        "visit_number": 1,
        "meets_criteria": True,
        "diagnosis": diagnosis,
        "date_of_diagnosis": "2026-07-15T08:00:00",
        "onset_class": OnsetClass.EOPE.value,
        "severity": SeverityGrade.WITH_SEVERE.value,
        "certainty": CertaintyLevel.DEFINITE.value,
        "rationale": "Independent third-reviewer adjudication rationale.",
    })


def test_reviewer_c_stickiness_blocks_unassigned_adjudicator():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        suffix = uuid.uuid4().hex[:6]
        a = f"sticky-a-{suffix}@acrnhealth.com"
        b = f"sticky-b-{suffix}@acrnhealth.com"
        c_assigned = f"sticky-c-{suffix}@acrnhealth.com"
        c_interloper = f"sticky-interloper-{suffix}@acrnhealth.com"

        # Seed the interloper user too
        db = TestingSession()
        db.query(PortalUser).filter_by(email=c_interloper).delete()
        db.add(PortalUser(
            email=c_interloper,
            display_name="Interloper",
            password_hash=hash_password(_PASSWORD),
            role="ADJUDICATOR",
            status="ACTIVE",
            is_demo_account=True,
        ))
        db.commit()
        db.close()

        case_number = _seed_discordant_case_with_reviewer_c(a, b, c_assigned)

        # Assigned C can submit
        result = _submit_c(case_number, c_assigned)
        assert result.status_code == 200, f"Assigned C should succeed: {result.text}"

        # Interloper cannot submit as C
        result2 = _submit_c(case_number, c_interloper)
        assert result2.status_code == 403, f"Unassigned adjudicator should be blocked: {result2.text}"
        assert "stickiness" in result2.json().get("detail", "").lower() or \
               "not assigned" in result2.json().get("detail", "").lower()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_reviewer_c_rejected_when_no_assignment_exists():
    """A REVIEWER_C submission on a case with no SubjectAssignment at all should return 409."""
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        suffix = uuid.uuid4().hex[:6]
        email = f"c-no-assign-{suffix}@acrnhealth.com"

        db = TestingSession()
        db.add(PortalUser(
            email=email,
            display_name="C No Assign",
            password_hash=hash_password(_PASSWORD),
            role="ADJUDICATOR",
            status="ACTIVE",
            is_demo_account=True,
        ))
        p = Participant(
            subject_id=f"NO-ASSIGN-{suffix}",
            case_number=f"ADJ-NO-ASSIGN-{suffix}",
            study=StudyCode.EOPE,
            status=AdjudicationStatus.IN_REVIEW,
            qc_approved=True,
        )
        db.add(p)
        db.commit()
        db.close()

        result = _submit_c(f"ADJ-NO-ASSIGN-{suffix}", email)
        assert result.status_code == 409, f"Expected 409, got {result.status_code}: {result.text}"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
