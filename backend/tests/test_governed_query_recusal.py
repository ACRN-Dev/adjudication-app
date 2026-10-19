import uuid

import pytest
from fastapi import HTTPException

from api import realtime
from models.auth import PortalUser
from models.longitudinal import ClinicalDataQuery, LongitudinalParticipant, ReviewerAssignment, ReviewerRecusal, RTImportBatch


def _case(db_session):
    batch = RTImportBatch(filename=f"workflow-{uuid.uuid4()}.csv", checksum=uuid.uuid4().hex + uuid.uuid4().hex, file_size=1, uploaded_by="monitor@example.org")
    db_session.add(batch); db_session.flush()
    participant = LongitudinalParticipant(blinded_subject_id=f"ACRN-{uuid.uuid4().hex[:12]}", study="PROTECT-Africa", source_batch_id=batch.id, workflow_status="ASSIGNED")
    db_session.add(participant); db_session.flush()
    return participant


def _user(db_session, email):
    user = PortalUser(email=email, display_name=email, role="ADJUDICATOR", status="ACTIVE", is_demo_account=True)
    db_session.add(user); db_session.flush(); return user


def test_query_is_persisted_and_monitor_closure_is_reasoned(db_session):
    participant = _case(db_session); _user(db_session, "reviewer@example.org")
    db_session.add(ReviewerAssignment(participant_id=participant.id, reviewer_upn="reviewer@example.org", reviewer_role="REVIEWER_A", status="ASSIGNED")); db_session.commit()
    created = realtime.raise_data_query(participant.id, realtime.DataQueryRequest(category="missing_timestamp", query_text="A confirmatory blood pressure timestamp is missing."), i=("reviewer@example.org","REVIEWER_A",False,{"*"}), db=db_session)
    row = db_session.get(ClinicalDataQuery, uuid.UUID(created["id"]))
    assert row.status == "OPEN"

    result = realtime.resolve_data_query(row.id, realtime.QueryResolutionRequest(response_text="Source timestamp supplied and verified.", closure_reason="Verified against certified source."), i=("monitor@example.org","MONITOR_QC_REVIEWER",True,{"*"}), db=db_session)
    assert result["status"] == "CLOSED"
    assert row.responded_by == "monitor@example.org"


def test_recusal_reassigns_stable_role_and_preserves_declaration(db_session, monkeypatch):
    monkeypatch.setattr(realtime, "_demo_contract_bypass_enabled", lambda: True)
    participant = _case(db_session)
    _user(db_session, "conflicted@example.org"); _user(db_session, "replacement@example.org")
    assignment = ReviewerAssignment(participant_id=participant.id, reviewer_upn="conflicted@example.org", reviewer_role="REVIEWER_A", status="ASSIGNED")
    db_session.add(assignment); db_session.commit()

    result = realtime.declare_recusal(participant.id, realtime.RecusalRequest(reason_code="clinical_care", comments="I provided direct clinical care to this participant."), i=("conflicted@example.org","REVIEWER_A",False,{"*"}), db=db_session)
    db_session.refresh(assignment)
    recusal = db_session.query(ReviewerRecusal).filter_by(participant_id=participant.id).one()
    assert result == {"id": str(recusal.id), "status": "RECUSED", "replacement_assigned": True}
    assert assignment.reviewer_upn == recusal.replacement_upn
    assert assignment.reviewer_upn != "conflicted@example.org"
    assert recusal.reviewer_upn == "conflicted@example.org"
    assert recusal.replacement_upn


def test_recused_reviewer_cannot_raise_another_query(db_session, monkeypatch):
    monkeypatch.setattr(realtime, "_demo_contract_bypass_enabled", lambda: True)
    participant = _case(db_session)
    _user(db_session, "former@example.org"); _user(db_session, "new@example.org")
    db_session.add(ReviewerAssignment(participant_id=participant.id, reviewer_upn="former@example.org", reviewer_role="REVIEWER_A", status="ASSIGNED")); db_session.commit()
    realtime.declare_recusal(participant.id, realtime.RecusalRequest(reason_code="personal", comments="A personal conflict requires independent reassignment."), i=("former@example.org","REVIEWER_A",False,{"*"}), db=db_session)
    with pytest.raises(HTTPException) as error:
        realtime.raise_data_query(participant.id, realtime.DataQueryRequest(category="missing_data", query_text="This query must not be accepted after recusal."), i=("former@example.org","REVIEWER_A",False,{"*"}), db=db_session)
    assert error.value.status_code == 403
