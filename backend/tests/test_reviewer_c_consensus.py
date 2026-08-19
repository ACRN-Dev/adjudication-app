"""
Tests for Reviewer C 3rd option, divergence checking, and committee escalation.
"""

import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from conftest import TestingSession
from database import get_db
from main import app
from models.canonical import (
    Participant, AdjudicationRecord, CommitteeDecision, StudyCode,
    ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus
)

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


def _seed_discordant_case():
    db = TestingSession()
    # Create participant
    p = Participant(
        study=StudyCode.EOPE,
        site_code="HARARE_01",
        subject_id=f"TEST-DISC-{uuid.uuid4().hex[:6].upper()}",
        status=AdjudicationStatus.DISCORDANT,
    )
    db.add(p)
    db.flush()

    # Reviewer A record
    rec_a = AdjudicationRecord(
        participant_id=p.id,
        reviewer_role=ReviewerRole.REVIEWER_A,
        reviewer_upn="adjudicatora@acrnhealth.com",
        reviewer_name="Reviewer A",
        diagnosis=DiagnosisCode.PREECLAMPSIA,
        onset_class=OnsetClass.EOPE,
        severity=SeverityGrade.WITH_SEVERE,
        certainty=CertaintyLevel.DEFINITE,
        rationale="Severe features confirmed with platelet drop",
        signed=True,
    )
    # Reviewer B record (divergent)
    rec_b = AdjudicationRecord(
        participant_id=p.id,
        reviewer_role=ReviewerRole.REVIEWER_B,
        reviewer_upn="adjudicatorb@acrnhealth.com",
        reviewer_name="Reviewer B",
        diagnosis=DiagnosisCode.GESTATIONAL_HTN,
        onset_class=OnsetClass.LOPE,
        severity=SeverityGrade.WITHOUT_SEVERE,
        certainty=CertaintyLevel.PROBABLE,
        rationale="No conclusive proteinuria",
        signed=True,
    )
    db.add_all([rec_a, rec_b])
    db.commit()
    subject_id = p.subject_id
    db.close()
    return subject_id


def test_list_discordant_cases():
    subject_id = _seed_discordant_case()
    r = client.get("/api/committee/discordant-cases")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    case = next((c for c in data["items"] if c["subject_id"] == subject_id), None)
    assert case is not None
    assert case["reviewer_a"]["diagnosis"] == "Pre-eclampsia"
    assert case["reviewer_b"]["diagnosis"] == "Gestational hypertension"


def test_reviewer_c_submits_matching_outcome_finalizes_concordance():
    subject_id = _seed_discordant_case()
    payload = {
        "reviewer_upn": "adjudicatorc@acrnhealth.com",
        "reviewer_name": "Reviewer C",
        "diagnosis": "Pre-eclampsia",
        "onset_class": "EOPE",
        "severity": "With severe features",
        "certainty": "Definite",
        "rationale": "Agree with Reviewer A based on thrombocytopenia lab evidence.",
        "visit_number": 1
    }
    r = client.post(f"/api/committee/{subject_id}/reviewer-c", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["concordance_status"] == "CONCORDANT_WITH_A"
    assert res["three_way_divergent"] is False


def test_reviewer_c_submits_independent_3rd_outcome_escalates_to_three_way_divergence():
    subject_id = _seed_discordant_case()
    payload = {
        "reviewer_upn": "adjudicatorc@acrnhealth.com",
        "reviewer_name": "Reviewer C",
        "diagnosis": "Chronic HTN",
        "onset_class": "EOPE",
        "severity": "Without severe features",
        "certainty": "Probable",
        "rationale": "Pre-existing baseline hypertension documented prior to 20 weeks gestation.",
        "visit_number": 1
    }
    r = client.post(f"/api/committee/{subject_id}/reviewer-c", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["concordance_status"] == "THREE_WAY_DIVERGENT"
    assert res["three_way_divergent"] is True
    assert res["participant_status"] == "THREE_WAY_DIVERGENT"


def test_committee_chair_locks_final_decision():
    subject_id = _seed_discordant_case()
    lock_payload = {
        "adopted_reviewer": "REVIEWER_A",
        "final_diagnosis": "Pre-eclampsia",
        "final_onset_class": "EOPE",
        "final_severity": "With severe features",
        "final_certainty": "Definite",
        "chair_rationale": "Committee reviewed clinical history and adopted Reviewer A diagnosis with quorum met.",
        "chair_upn": "chairperson@acrnhealth.com",
        "chair_name": "Committee Chair",
        "quorum_met": True,
        "members_present": 4,
        "visit_number": 1
    }
    r = client.post(f"/api/committee/{subject_id}/lock", json=lock_payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["final_diagnosis"] == "Pre-eclampsia"
    assert "signature_hash" in res
