import uuid

import pytest
from fastapi import HTTPException

from api import realtime
from api.realtime import assign
from conftest import TestingSession
from models.auth import PortalUser
from models.longitudinal import LongitudinalParticipant, RTImportBatch, ReviewerAssignment, VisitInstance


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
    db.flush()
    db.add(VisitInstance(
        participant_id=new_participant.id,
        source_batch_id=batch.id,
        form_title="Visit 1",
        scheduled_visit_code="V01",
        visit_sequence=1,
        reconstruction_method="TEST",
        reconstruction_confidence="HIGH",
    ))
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


def test_completed_assignments_do_not_consume_capacity(monkeypatch):
    db = TestingSession()
    suffix = uuid.uuid4().hex[:8]
    reviewer_email = f"completed-capacity-{suffix}@acrnhealth.com"
    batch = RTImportBatch(
        filename=f"completed-capacity-{suffix}.csv",
        checksum=uuid.uuid4().hex,
        file_size=1,
        uploaded_by="monitor@acrnhealth.com",
    )
    db.add(batch)
    db.add(PortalUser(
        email=reviewer_email,
        display_name="Completed Capacity Reviewer",
        role="ADJUDICATOR",
        status="ACTIVE",
    ))
    db.flush()

    for idx in range(6):
        participant = LongitudinalParticipant(
            blinded_subject_id=f"DONE-{suffix}-{idx}" if idx == 0 else f"ACTIVE-{suffix}-{idx}",
            study="PROTECT-Africa",
            source_batch_id=batch.id,
            workflow_status="ASSIGNED",
        )
        db.add(participant)
        db.flush()
        db.add(ReviewerAssignment(
            participant_id=participant.id,
            reviewer_upn=reviewer_email,
            reviewer_role="REVIEWER_A",
            status="ASSIGNED",
        ))
    db.commit()

    monkeypatch.setattr(
        realtime,
        "completion_state",
        lambda _db, participant: (participant.blinded_subject_id.startswith("DONE-"), 1),
    )
    try:
        assert realtime.active_assignment_workloads(db)[reviewer_email] == 5
    finally:
        db.close()
