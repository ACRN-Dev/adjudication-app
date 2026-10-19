import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from api import realtime
from models.longitudinal import CanonicalObservation, LongitudinalParticipant, ObservationCorrection, RTImportBatch, VisitDerivation, VisitInstance


def _seed_observation(db_session):
    batch=RTImportBatch(filename=f"correction-{uuid.uuid4()}.csv",checksum=uuid.uuid4().hex+uuid.uuid4().hex,file_size=10,uploaded_by="importer@example.org")
    db_session.add(batch); db_session.flush()
    participant=LongitudinalParticipant(blinded_subject_id=f"ACRN-{uuid.uuid4().hex[:12]}",study="PROTECT-Africa",source_batch_id=batch.id,workflow_status="MONITOR_QC_REQUIRED")
    db_session.add(participant); db_session.flush()
    visit=VisitInstance(participant_id=participant.id,source_batch_id=batch.id,form_title="Visit 1",scheduled_visit_code="V01",visit_sequence=1,visit_datetime=datetime(2026,1,1),reconstruction_method="TEST",reconstruction_confidence="HIGH")
    db_session.add(visit); db_session.flush()
    observation=CanonicalObservation(participant_id=participant.id,visit_id=visit.id,source_batch_id=batch.id,canonical_variable="PLATELETS",raw_source_value="150",parsed_text_value="150",numeric_value=150,unit="10^9/L",observation_datetime=datetime(2026,1,1),source_form="Visit 1",source_page="Labs",source_field_label="Platelets",source_row_number=5,mapping_version="RT-MAP-1.0",quality_status="VALID",documentation_status="Documented",provenance_type="SOURCE_RECORDED",source_fingerprint=uuid.uuid4().hex)
    db_session.add(observation); db_session.commit()
    return participant, visit, observation


def test_correction_requires_independent_approval_and_rederives(db_session):
    participant, visit, original = _seed_observation(db_session)
    requested=realtime.request_observation_correction(original.id,realtime.CorrectionRequest(raw_source_value="90",unit="10^9/L",observation_datetime=datetime(2026,1,1),reason="Certified source verification found a transcription error."),i=("requester@example.org","MONITOR_QC_REVIEWER",True,{"*"}),db=db_session)
    correction=db_session.get(ObservationCorrection,uuid.UUID(requested["id"]))

    with pytest.raises(HTTPException) as error:
        realtime.approve_observation_correction(correction.id,realtime.CorrectionApprovalRequest(reason="Attempted self approval is prohibited by procedure."),i=("requester@example.org","MONITOR_QC_REVIEWER",True,{"*"}),db=db_session)
    assert error.value.status_code==409

    approved=realtime.approve_observation_correction(correction.id,realtime.CorrectionApprovalRequest(reason="Compared with the certified source and approved replacement."),i=("approver@example.org","QA_REVIEWER",True,{"*"}),db=db_session)
    db_session.refresh(original)
    replacement=db_session.get(CanonicalObservation,uuid.UUID(approved["replacement_observation_id"]))
    assert original.superseded is True
    assert replacement.numeric_value==90
    assert replacement.supersedes_observation_id==original.id
    assert replacement.provenance_type=="SOURCE_CORRECTION"
    dv08=db_session.query(VisitDerivation).filter_by(visit_id=visit.id,dv_identifier="DV-08").one()
    assert dv08.result["met"] is True


def test_timeline_excludes_superseded_value(db_session):
    participant, _, original = _seed_observation(db_session)
    correction=realtime.request_observation_correction(original.id,realtime.CorrectionRequest(raw_source_value="90",reason="Certified source verification found a transcription error."),i=("requester2@example.org","MONITOR_QC_REVIEWER",True,{"*"}),db=db_session)
    realtime.approve_observation_correction(uuid.UUID(correction["id"]),realtime.CorrectionApprovalRequest(reason="Independent source comparison confirms the corrected value."),i=("approver2@example.org","QA_REVIEWER",True,{"*"}),db=db_session)
    payload=realtime.timeline(participant,db_session)
    values=payload["visits"][0]["evidence"]["PLATELETS"]
    assert [row["value"] for row in values]==[90.0]
    assert values[0]["supersedes_observation_id"]==str(original.id)
