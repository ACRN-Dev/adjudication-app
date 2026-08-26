import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from conftest import TestingSession
from models.canonical import (
    AdjudicationRecord, AdjudicationVisit, DiagnosisCode, Participant,
    ReviewerRole, StudyCode, VisitMeasurementDate,
)


def _participant(db):
    suffix = uuid.uuid4().hex[:8]
    participant = Participant(
        subject_id=f"VISIT-{suffix}", case_number=f"ADJ-{suffix}", study=StudyCode.EOPE
    )
    db.add(participant)
    db.flush()
    return participant


def test_subject_visit_is_the_unique_adjudication_key_and_dates_sort_chronologically():
    db = TestingSession()
    try:
        participant = _participant(db)
        visit = AdjudicationVisit(
            participant_id=participant.id, visit_number=2, visit_code="V02",
            visit_date=datetime(2026, 8, 20),
        )
        db.add(visit)
        db.flush()
        later = datetime(2026, 8, 20, 11)
        earlier = later - timedelta(hours=3)
        db.add_all([
            VisitMeasurementDate(visit_id=visit.id, measurement_type="LAB", measured_at=later),
            VisitMeasurementDate(visit_id=visit.id, measurement_type="BP", measured_at=earlier),
        ])
        db.commit()
        db.refresh(visit)
        assert [m.measured_at for m in visit.measurement_dates] == [earlier, later]

        db.add(AdjudicationVisit(
            participant_id=participant.id, visit_number=2, visit_code="V02-duplicate"
        ))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_other_is_reviewer_c_only_and_requires_rationale_at_database_boundary():
    db = TestingSession()
    try:
        participant = _participant(db)
        visit = AdjudicationVisit(participant_id=participant.id, visit_number=1, visit_code="V01")
        db.add(visit)
        db.flush()
        db.add(AdjudicationRecord(
            participant_id=participant.id, visit_id=visit.id, visit_number=1,
            reviewer_role=ReviewerRole.REVIEWER_A, reviewer_upn="a@example.test",
            diagnosis=DiagnosisCode.OTHER, rationale="comment", signed=True,
        ))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()

    db = TestingSession()
    try:
        participant = _participant(db)
        visit = AdjudicationVisit(participant_id=participant.id, visit_number=1, visit_code="V01")
        db.add(visit)
        db.flush()
        db.add(AdjudicationRecord(
            participant_id=participant.id, visit_id=visit.id, visit_number=1,
            reviewer_role=ReviewerRole.REVIEWER_C, reviewer_upn="c@example.test",
            diagnosis=DiagnosisCode.OTHER, rationale="comment",
            other_rationale="Evidence supports a diagnosis outside the standard list.", signed=True,
        ))
        db.commit()
    finally:
        db.close()


def test_standard_outcome_list_is_closed():
    assert {item.value for item in DiagnosisCode} == {
        "PE", "Severe PE", "Eclampsia", "HELLP", "Other"
    }
