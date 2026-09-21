import uuid

import pytest
from fastapi import HTTPException

from api.realtime import assign
from conftest import TestingSession
from models.auth import PortalUser
from models.longitudinal import LongitudinalParticipant, RTImportBatch, ReviewerAssignment


def test_assignment_rejects_over_capacity_reviewer(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_DATA", "false")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")

    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]
    reviewer_email = f"capacity-reviewer-{suffix}@acrnhealth.com"
    batch = RTImportBatch(
        filename=f"capacity-{suffix}.csv",
        checksum=uuid.uuid4().hex,
        file_size=1,
        uploaded_by="monitor@acrnhealth.com",
    )
    db.add(batch)
    db.flush()

    reviewer = PortalUser(
        email=reviewer_email,
        display_name="Capacity Reviewer",
        role="ADJUDICATOR",
        status="ACTIVE",
    )
    db.add(reviewer)

    for idx in range(8):
        participant = LongitudinalParticipant(
            blinded_subject_id=f"CAP-{suffix}-{idx}",
            study="PROTECT-Africa",
            source_batch_id=batch.id,
            workflow_status="QC_APPROVED",
        )
        db.add(participant)
        db.flush()
        db.add(
            ReviewerAssignment(
                participant_id=participant.id,
                reviewer_upn=reviewer_email,
                reviewer_role="REVIEWER_A",
                status="ASSIGNED",
            )
        )

    new_participant = LongitudinalParticipant(
        blinded_subject_id=f"CAP-{suffix}-NEW",
        study="PROTECT-Africa",
        source_batch_id=batch.id,
        workflow_status="QC_APPROVED",
    )
    db.add(new_participant)
    db.commit()

    try:
        with pytest.raises(HTTPException) as exc:
            assign(
                new_participant.id,
                reviewer_email,
                "REVIEWER_A",
                i=("monitor@acrnhealth.com", "MONITOR_QC_REVIEWER", True),
                db=db,
            )
        assert exc.value.status_code == 409
        assert "capacity" in str(exc.value.detail).lower()
    finally:
        db.close()