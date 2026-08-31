import uuid

import pytest
from fastapi import HTTPException

from api.realtime import assign
from api.adjudication import _demo_validation_bypass_enabled
from conftest import TestingSession
from models.auth import PortalUser
from models.longitudinal import LongitudinalParticipant, RTImportBatch, ReviewerAssignment


def _seed_assignment_target():
    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]
    reviewer_email = f"demo-contract-{suffix}@acrnhealth.com"
    batch = RTImportBatch(
        filename=f"demo-contract-{suffix}.csv",
        checksum=uuid.uuid4().hex,
        file_size=1,
        uploaded_by="monitor@acrnhealth.com",
    )
    db.add(batch)
    db.flush()
    participant = LongitudinalParticipant(
        blinded_subject_id=f"CONTRACT-{suffix}",
        study="PROTECT-Africa",
        source_batch_id=batch.id,
        workflow_status="QC_APPROVED",
    )
    reviewer = PortalUser(
        email=reviewer_email,
        display_name="Demo Contract Reviewer",
        role="ADJUDICATOR",
        status="ACTIVE",
    )
    db.add_all([participant, reviewer])
    db.commit()
    return db, participant.id, reviewer_email


def test_demo_data_mode_skips_contract_verification(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_DATA", "true")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db, participant_id, reviewer_email = _seed_assignment_target()
    try:
        result = assign(
            participant_id,
            reviewer_email,
            "REVIEWER_A",
            i=("monitor@acrnhealth.com", "MONITOR_QC_REVIEWER", True),
            db=db,
        )
        assert result == {"status": "ASSIGNED", "contract_verification": "BYPASSED_DEMO"}
        assert db.query(ReviewerAssignment).filter_by(
            participant_id=participant_id,
            reviewer_upn=reviewer_email,
            reviewer_role="REVIEWER_A",
        ).one()
    finally:
        db.close()


def test_non_demo_mode_still_requires_active_contract(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_DATA", "false")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db, participant_id, reviewer_email = _seed_assignment_target()
    try:
        with pytest.raises(HTTPException) as exc:
            assign(
                participant_id,
                reviewer_email,
                "REVIEWER_A",
                i=("monitor@acrnhealth.com", "MONITOR_QC_REVIEWER", True),
                db=db,
            )
        assert exc.value.status_code == 409
        assert "active contract" in str(exc.value.detail).lower()
    finally:
        db.close()


def test_cross_visit_date_bypass_is_demo_only(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_DATA", "true")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    assert _demo_validation_bypass_enabled() is True
    monkeypatch.setenv("ENABLE_DEMO_DATA", "false")
    assert _demo_validation_bypass_enabled() is False
