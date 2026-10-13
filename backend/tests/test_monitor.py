import os,sys,pytest
import uuid
from datetime import datetime
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from services.monitor_security import scan_blinding,validate_import,qc_gate,assignment_gate,release_gate
from services.workflow_policy import check_reviewer_isolation,check_committee_quorum,evaluate_concordance
from conftest import TestingSession
from models.longitudinal import CanonicalObservation, RTImportBatch, LongitudinalParticipant, ReviewerAssignment, VisitInstance
from models.canonical import AdjudicationRecord, AdjudicationVisit, Participant, ReviewerRole, StudyCode

client = TestClient(app)


def test_prohibited_fields_quarantined(): assert scan_blinding(['export_PlGF.csv'])['state']=='UNBLINDING_QUARANTINE'
def test_clean_blinded_file_passes(): assert scan_blinding(['edc_bp.csv'])['passed']
def test_duplicate_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','same',['participant_id'],[{'participant_id':'1'}],{'same'})
def test_empty_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['participant_id'],[],set())
def test_required_header_enforced():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['bp'],[{'bp':120}],set())
def test_mandatory_pre_qc_blocks_release():
    with pytest.raises(HTTPException): qc_gate([{'mandatory':True,'response':'Fail'}])
def test_pre_qc_passes(): qc_gate([{'mandatory':True,'response':'Pass'},{'mandatory':False,'response':'N/A'}])
def test_same_reviewer_cannot_fill_both_roles():
    with pytest.raises(HTTPException): assignment_gate('a','a',{'a'})
def test_ineligible_reviewer_rejected():
    with pytest.raises(HTTPException): assignment_gate('a','b',{'a'})
def test_reviewer_isolation_preserved(): assert check_reviewer_isolation('A','B','QA_RELEASED') is False
def test_concordance_and_discordance():
    a={'primary_diagnosis':'PE','onset_classification':'EOPE','severity_phenotype':'severe','certainty_level':'definite'}
    assert evaluate_concordance(a,a)['concordant']; b={**a,'certainty_level':'probable'}; assert not evaluate_concordance(a,b)['concordant']
def test_committee_quorum_gate(): assert not check_committee_quorum(2).allowed and check_committee_quorum(3).allowed
def test_final_qc_gate():
    with pytest.raises(HTTPException): release_gate('Fail',True)
    with pytest.raises(HTTPException): release_gate('Pass',False)
    release_gate('Pass',True)


def test_monitor_headers_rejected_when_demo_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 401


def test_monitor_headers_accepted_when_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 200


def test_monitor_session_grants_access_using_portal_role(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    db = TestingSession()
    db.add(PortalUser(
        email="sso.monitor@acrnhealth.com", display_name="SSO Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    session_client = TestClient(app)
    login = session_client.post("/api/auth/login", json={"email": "sso.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = session_client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200
    assert r.json()["role"] == "MONITOR_QC_REVIEWER"


def test_monitor_session_without_portal_role_denied(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role.monitor@acrnhealth.com", display_name="No Portal Role Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    session_client = TestClient(app)
    login = session_client.post("/api/auth/login", json={"email": "no.portal.role.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = session_client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403


def test_monitor_operational_dashboard_uses_visit_level_counts(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/monitor/operational-dashboard", headers={"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["available_visits"] >= 1
    assert body["summary"]["overall_completion_pct"] >= 0
    assert body["summary"]["completed_visits"] >= 0
    assert "available_visits" in body["summary"]
    assert "by_status" in body
    assert "adjudicators" in body


def test_monitor_progress_deduplicates_same_blinded_case_across_sources(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/realtime/progress", headers={"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["unique_cases"] == len(body["items"])
    assert body["summary"]["total_visits"] >= body["summary"]["adjudicated_visits"]
    assert "duplicate_source_records" in body["summary"]
    assert set(body["by_case_status"]) == {"PENDING", "IN_PROGRESS", "ADJUDICATED_CLOSED"}


def test_monitor_progress_collapses_duplicate_source_batches(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    subject_id = f"ACRN-DUP-{uuid.uuid4().hex[:8].upper()}"
    batches = [
        RTImportBatch(filename=f"duplicate-{index}.csv", checksum=uuid.uuid4().hex, file_size=10, uploaded_by="monitor1@acrnhealth.com")
        for index in (1, 2)
    ]
    db.add_all(batches)
    db.flush()
    participants = [
        LongitudinalParticipant(blinded_subject_id=subject_id, source_batch_id=batch.id, study="PROTECT-Africa")
        for batch in batches
    ]
    db.add_all(participants)
    db.flush()
    db.add_all([
        VisitInstance(
            participant_id=participant.id, source_batch_id=participant.source_batch_id,
            form_title="Visit 1", scheduled_visit_code="V01", visit_sequence=1,
            reconstruction_method="TEST", reconstruction_confidence="HIGH",
        )
        for participant in participants
    ])
    db.commit()
    db.close()

    response = TestClient(app).get("/api/realtime/progress", headers={"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert response.status_code == 200, response.text
    item = next(row for row in response.json()["items"] if row["subject_id"] == subject_id)
    assert item["total_visits"] == 1
    assert item["duplicate_source_count"] == 1


def test_reviewer_progress_counts_only_the_requesting_reviewers_signed_visits(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    subject_id = f"REVIEWER-PROGRESS-{uuid.uuid4().hex[:8].upper()}"
    batch = RTImportBatch(
        filename="reviewer-progress.csv",
        checksum=uuid.uuid4().hex,
        file_size=10,
        uploaded_by="monitor1@acrnhealth.com",
    )
    db.add(batch)
    db.flush()
    rt_participant = LongitudinalParticipant(
        blinded_subject_id=subject_id,
        source_batch_id=batch.id,
        study="PROTECT-Africa",
        workflow_status="ASSIGNED",
    )
    canonical = Participant(subject_id=subject_id, study=StudyCode.EOPE)
    db.add_all([rt_participant, canonical])
    db.flush()
    visits = [
        AdjudicationVisit(
            participant_id=canonical.id,
            visit_number=visit_number,
            visit_code=f"V{visit_number:02d}",
            status="IN_REVIEW",
        )
        for visit_number in (1, 2)
    ]
    db.add_all(visits)
    db.flush()
    db.add_all([
        ReviewerAssignment(
            participant_id=rt_participant.id,
            reviewer_upn="adjudicatora@acrnhealth.com",
            reviewer_role="REVIEWER_A",
            status="ASSIGNED",
        ),
        ReviewerAssignment(
            participant_id=rt_participant.id,
            reviewer_upn="adjudicatorb@acrnhealth.com",
            reviewer_role="REVIEWER_B",
            status="ASSIGNED",
        ),
        AdjudicationRecord(
            participant_id=canonical.id,
            visit_id=visits[0].id,
            visit_number=1,
            reviewer_role=ReviewerRole.REVIEWER_A,
            reviewer_upn="adjudicatora@acrnhealth.com",
            signed=True,
        ),
        *[
            AdjudicationRecord(
                participant_id=canonical.id,
                visit_id=visit.id,
                visit_number=visit.visit_number,
                reviewer_role=ReviewerRole.REVIEWER_B,
                reviewer_upn="adjudicatorb@acrnhealth.com",
                signed=True,
            )
            for visit in visits
        ],
    ])
    db.commit()
    db.close()

    progress_client = TestClient(app)
    reviewer_a = progress_client.get(
        "/api/realtime/progress",
        headers={"X-Demo-User": "adjudicatora@acrnhealth.com", "X-Demo-Role": "ADJUDICATOR"},
    )
    reviewer_b = progress_client.get(
        "/api/realtime/progress",
        headers={"X-Demo-User": "adjudicatorb@acrnhealth.com", "X-Demo-Role": "ADJUDICATOR"},
    )
    assert reviewer_a.status_code == 200, reviewer_a.text
    assert reviewer_b.status_code == 200, reviewer_b.text
    item_a = next(item for item in reviewer_a.json()["items"] if item["subject_id"] == subject_id)
    item_b = next(item for item in reviewer_b.json()["items"] if item["subject_id"] == subject_id)
    assert item_a["status"] == "PENDING"
    assert item_a["reviewer_status"] == "IN_PROGRESS"
    assert item_a["reviewer_signed_visits"] == 1
    assert item_a["reviewer_pending_visits"] == 1
    assert item_b["reviewer_status"] == "COMPLETED"
    assert item_b["reviewer_signed_visits"] == 2
    assert item_b["reviewer_pending_visits"] == 0


def test_conflicting_dates_block_qc_approval_without_date_label(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    participant = LongitudinalParticipant(
        blinded_subject_id=f"DATE-CONFLICT-{uuid.uuid4().hex[:8].upper()}",
        study="PROTECT-Africa",
        source_batch_id=uuid.uuid4(),
        workflow_status="MONITOR_QC_REQUIRED",
    )
    db.add(participant)
    db.flush()
    db.add(VisitInstance(
        participant_id=participant.id,
        source_batch_id=participant.source_batch_id,
        form_title="Visit 1",
        scheduled_visit_code="V01",
        visit_sequence=1,
        visit_occurrence=1,
        reconstruction_method="TEST",
        reconstruction_confidence="HIGH",
        qc_status="MONITOR_QC_REQUIRED",
    ))
    db.flush()
    visit = db.query(VisitInstance).filter_by(participant_id=participant.id).one()
    db.add_all([
        CanonicalObservation(
            participant_id=participant.id,
            visit_id=visit.id,
            source_batch_id=participant.source_batch_id,
            canonical_variable="EDD",
            datetime_value=datetime(2026, 1, 1),
        ),
        CanonicalObservation(
            participant_id=participant.id,
            visit_id=visit.id,
            source_batch_id=participant.source_batch_id,
            canonical_variable="EDD",
            datetime_value=datetime(2026, 2, 1),
        ),
    ])
    db.commit()
    participant_id = str(participant.id)
    db.close()

    response = TestClient(app).post(
        f"/api/realtime/patients/{participant_id}/approve",
        headers={"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"},
    )
    assert response.status_code == 409, response.text
    assert "Monitor/QC review" in response.json()["detail"]
