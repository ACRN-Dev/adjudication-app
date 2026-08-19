"""
Tests for Chairperson workspace, completed adjudications, agenda pack, and meeting sign-off.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from conftest import TestingSession
from database import get_db
from main import app
from models.canonical import (
    Participant, AdjudicationRecord, CommitteeDecision, CommitteeMeeting, StudyCode,
    ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus
)
from models.auth import PortalUser, CommitteeAssignment
from services.auth_service import current_user

def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def use_db_override():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def _seed_completed_case(concordant=True):
    db = TestingSession()
    p = Participant(
        study=StudyCode.EOPE,
        site_code="HARARE_02",
        subject_id=f"CHAIR-TEST-{uuid.uuid4().hex[:6].upper()}",
        status=AdjudicationStatus.CONCORDANT if concordant else AdjudicationStatus.DISCORDANT,
    )
    db.add(p)
    db.flush()

    rec_a = AdjudicationRecord(
        participant_id=p.id,
        reviewer_role=ReviewerRole.REVIEWER_A,
        reviewer_upn="adjudicatora@acrnhealth.com",
        reviewer_name="Reviewer A",
        diagnosis=DiagnosisCode.PREECLAMPSIA,
        onset_class=OnsetClass.EOPE,
        severity=SeverityGrade.WITH_SEVERE,
        certainty=CertaintyLevel.DEFINITE,
        rationale="Criteria met",
        signed=True,
    )
    rec_b = AdjudicationRecord(
        participant_id=p.id,
        reviewer_role=ReviewerRole.REVIEWER_B,
        reviewer_upn="adjudicatorb@acrnhealth.com",
        reviewer_name="Reviewer B",
        diagnosis=DiagnosisCode.PREECLAMPSIA if concordant else DiagnosisCode.NOT_PE,
        onset_class=OnsetClass.EOPE if concordant else None,
        severity=SeverityGrade.WITH_SEVERE if concordant else None,
        certainty=CertaintyLevel.DEFINITE if concordant else CertaintyLevel.PROBABLE,
        rationale="Criteria met" if concordant else "Normotensive profile",
        signed=True,
    )
    db.add_all([rec_a, rec_b])
    db.commit()
    subject_id = p.subject_id
    db.close()
    return subject_id


def _chairperson_user_with_assignment():
    db = TestingSession()
    email = "chairperson@acrnhealth.com"
    user = db.query(PortalUser).filter_by(email=email).first()
    if not user:
        user = PortalUser(
            id="chairperson-assigned-user",
            email=email,
            display_name="Assigned Chairperson",
            role="CHAIRPERSON",
            status="ACTIVE",
            is_demo_account=True,
        )
        db.add(user)
        db.flush()

    assignment = (
        db.query(CommitteeAssignment)
        .filter_by(user_id=user.id, assignment_type="CHAIRPERSON", status="ACTIVE")
        .first()
    )
    if not assignment:
        db.add(CommitteeAssignment(
            user_id=user.id,
            assignment_type="CHAIRPERSON",
            committee_name="PROTECT-Africa Committee",
            is_active=True,
            status="ACTIVE",
            assignment_metadata={"source": "test"},
        ))
    db.commit()
    return db.query(PortalUser).filter_by(email=email).one()


def test_chairperson_list_completed_adjudications():
    subj_conc = _seed_completed_case(concordant=True)
    subj_disc = _seed_completed_case(concordant=False)

    user = _chairperson_user_with_assignment()
    previous = app.dependency_overrides.get(current_user)
    app.dependency_overrides[current_user] = lambda: user
    try:
        r = client.get("/api/chairperson/completed-adjudications")
    finally:
        if previous is None:
            app.dependency_overrides.pop(current_user, None)
        else:
            app.dependency_overrides[current_user] = previous

    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert data["summary"]["concordant"] >= 1
    assert data["summary"]["discordant"] >= 1

    item_conc = next((i for i in data["items"] if i["subject_id"] == subj_conc), None)
    assert item_conc is not None
    assert item_conc["concordance"] == "CONCORDANT_A_EQUALS_B"

    item_disc = next((i for i in data["items"] if i["subject_id"] == subj_disc), None)
    assert item_disc is not None
    assert item_disc["concordance"] == "DISCORDANT_A_NEQ_B"


def test_chairperson_requires_active_assignment():
    user = PortalUser(
        id="chair-assignment-test-user",
        email="unassigned-chair@acrnhealth.com",
        display_name="Unassigned Chair",
        role="CHAIRPERSON",
        status="ACTIVE",
        is_demo_account=True,
    )

    previous = app.dependency_overrides.get(current_user)
    app.dependency_overrides[current_user] = lambda: user
    try:
        r = client.get("/api/chairperson/completed-adjudications")
        assert r.status_code == 403
        assert "assignment" in r.json().get("detail", "").lower()
    finally:
        if previous is None:
            app.dependency_overrides.pop(current_user, None)
        else:
            app.dependency_overrides[current_user] = previous


def test_chairperson_generate_agenda_pack():
    _seed_completed_case(concordant=True)
    _seed_completed_case(concordant=False)

    user = _chairperson_user_with_assignment()
    previous = app.dependency_overrides.get(current_user)
    app.dependency_overrides[current_user] = lambda: user
    try:
        r = client.get("/api/chairperson/agenda-pack?batch_id=BATCH-2026-08")
    finally:
        if previous is None:
            app.dependency_overrides.pop(current_user, None)
        else:
            app.dependency_overrides[current_user] = previous

    assert r.status_code == 200
    pack = r.json()
    assert "pack_id" in pack
    assert pack["batch_id"] == "BATCH-2026-08"
    assert pack["total_cases"] >= 2
    assert "items_for_committee_arbitration" in pack
    assert "concordant_cases_consent_calendar" in pack


def test_chairperson_sign_off_meeting_and_close_cases():
    subj = _seed_completed_case(concordant=True)
    user = _chairperson_user_with_assignment()
    previous = app.dependency_overrides.get(current_user)
    app.dependency_overrides[current_user] = lambda: user

    payload = {
        "meeting_title": "PROTECT-Africa Adjudication Batch 1 Meeting",
        "batch_id": "BATCH-01",
        "attendees": ["chairperson@acrnhealth.com", "adjudicatora@acrnhealth.com", "adjudicatorb@acrnhealth.com"],
        "quorum_met": True,
        "minutes": "Meeting convened at 14:00. All reviewed cases verified. Consensus confirmed on all agenda items.",
        "case_ids": [subj],
        "chair_name": "ACRN Committee Chairperson"
    }

    try:
        r = client.post("/api/chairperson/meetings/sign-off", json=payload)
    finally:
        if previous is None:
            app.dependency_overrides.pop(current_user, None)
        else:
            app.dependency_overrides[current_user] = previous

    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["closed_cases_count"] == 1
    assert "signature_hash" in res

    # Verify participant is now CLOSED
    db = TestingSession()
    p = db.query(Participant).filter_by(subject_id=subj).one()
    assert p.status == AdjudicationStatus.CLOSED
    db.close()

    # Verify meetings list endpoint
    previous = app.dependency_overrides.get(current_user)
    app.dependency_overrides[current_user] = lambda: user
    try:
        r_list = client.get("/api/chairperson/meetings")
    finally:
        if previous is None:
            app.dependency_overrides.pop(current_user, None)
        else:
            app.dependency_overrides[current_user] = previous

    assert r_list.status_code == 200
    meetings = r_list.json()
    assert len(meetings["items"]) >= 1
    assert any(m["title"] == "PROTECT-Africa Adjudication Batch 1 Meeting" for m in meetings["items"])
