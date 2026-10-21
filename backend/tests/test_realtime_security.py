"""RealTime API authorization tests: closes the header-trust bypass in backend/api/realtime.py.

This is the Monitor Portal's ACTUAL backend (the frontend calls /api/realtime/*, not
/api/monitor/*). Mirrors the pattern established in test_admin.py and test_monitor.py for
the sibling admin_security.py / monitor_security.py fixes.
"""
import os, sys
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import app
from models.auth import PortalUser
from models.longitudinal import LongitudinalParticipant, RTImportBatch, ReviewerAssignment
from services.auth_service import ACTIVE, hash_password
from conftest import TestingSession

client = TestClient(app)

# Against a non-existent participant an authorised caller gets 404 and an unauthorised one 403,
# which cleanly separates "no authority" from "allowed but nothing there".
QC_DECISION = "/api/realtime/patients/00000000-0000-0000-0000-000000000000/approve"


def test_realtime_headers_rejected_when_demo_disabled_and_no_session(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/realtime/batches", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"})
    assert r.status_code == 401


def test_realtime_headers_accepted_when_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/realtime/batches", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"})
    assert r.status_code == 200


def test_realtime_session_with_valid_portal_role_grants_access(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.monitor@acrnhealth.com", display_name="SSO RealTime Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/realtime/batches", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_realtime_session_without_portal_role_rejected(monkeypatch):
    """A Monitor account without an approved portal role has no RealTime authority."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role.realtime@acrnhealth.com", display_name="No Portal Role RealTime",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="INVALID_ROLE", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role.realtime@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    cookies = {"acrn_demo_session": login.cookies["acrn_demo_session"]}
    assert client.post(QC_DECISION, cookies=cookies).status_code == 403
    assert client.get("/api/realtime/batches", cookies=cookies).status_code == 403
    assert client.get("/api/realtime/patients", cookies=cookies).status_code == 403


def test_realtime_non_monitor_session_rejected_even_with_spoofed_headers(monkeypatch):
    """The header-trust bypass stays closed: a session never falls through to X-Demo-*."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.adjudicator@acrnhealth.com", display_name="SSO RealTime Adjudicator",
        password_hash=hash_password("Whatever123!"), role="ADJUDICATOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.adjudicator@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.post(
        QC_DECISION,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
        headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"},
    )
    assert r.status_code == 403


def test_realtime_adjudicator_session_without_portal_role_can_reach_assigned(monkeypatch):
    """The whole reason actor()'s non-MONITOR branch has an explicit ADJUDICATOR allow-list:
    /assigned depends on actor() directly (not monitor()) and adjudicators typically have no
    portal_role at all. This must keep working after the allow-list tightening."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.adjudicator.noportal@acrnhealth.com", display_name="SSO RealTime Adjudicator No Portal Role",
        password_hash=hash_password("Whatever123!"), role="ADJUDICATOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.adjudicator.noportal@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/realtime/assigned", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_realtime_monitor_session_invalid_portal_role_definitive_even_when_demo_enabled_with_valid_headers(monkeypatch):
    """Proves the session's rejection isn't merely reachable-but-untested when demo mode is
    off (the earlier test only covered ENABLE_DEMO_ACCOUNTS=false, where headers are
    unreachable anyway). Here demo mode is ON and the accompanying headers are valid MONITOR
    credentials on their own -- the under-provisioned session must still win with a 403,
    never silently falling through to the headers."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.realtime.monitor.badportal@acrnhealth.com", display_name="SSO RealTime Monitor Bad Portal Role",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="INVALID_ROLE", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.realtime.monitor.badportal@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.post(
        QC_DECISION,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
        headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR"},
    )
    assert r.status_code == 403


def test_medical_officer_can_access_case_data_but_not_adjudication_operations(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.medical.officer@acrnhealth.com", display_name="SSO Medical Officer",
        password_hash=hash_password("Whatever123!"), role="MEDICAL_OFFICER", portal_role="MEDICAL_OFFICER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.medical.officer@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    cookies = {"acrn_demo_session": login.cookies["acrn_demo_session"]}

    assert client.get("/api/realtime/batches", cookies=cookies).status_code == 200
    assert client.get("/api/realtime/patients", cookies=cookies).status_code == 200
    assert client.get("/api/realtime/queries", cookies=cookies).status_code == 200
    assert client.get("/api/realtime/adjudicators", cookies=cookies).status_code == 403
    assert client.post(QC_DECISION, cookies=cookies).status_code == 403


def test_realtime_session_monitor_can_upload_batch(monkeypatch):
    import io, uuid
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.upload.monitor@acrnhealth.com", display_name="SSO Upload Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.upload.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200

    csv_content = (
        "MRN,Screening #,Randomization #,Form Title,Form Version,Page Title,Field type,Field Label,Data Input,Data Value,Audit Trails,Export Variable Name\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-001,RAND-001,Visit 1,v1.0,Vitals,text,Systolic Blood Pressure,120,120,,SBP\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-001,RAND-001,Visit 1,v1.0,Vitals,text,Diastolic Blood Pressure,80,80,,DBP\n"
    )
    files = {"file": ("test_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    r = client.post(
        "/api/realtime/batches",
        files=files,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["filename"] == "test_batch.csv"
    assert data["status"] in {"CHECKSUM_CALCULATED", "ROWS_STAGED", "VISITS_RECONSTRUCTED", "MONITOR_QC_REQUIRED"}


def test_realtime_session_admin_can_upload_batch(monkeypatch):
    import io, uuid
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.upload.admin@acrnhealth.com", display_name="SSO Upload Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.upload.admin@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200

    csv_content = (
        "MRN,Screening #,Randomization #,Form Title,Form Version,Page Title,Field type,Field Label,Data Input,Data Value,Audit Trails,Export Variable Name\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-002,RAND-002,Visit 1,v1.0,Vitals,text,Systolic Blood Pressure,130,130,,SBP\n"
    )
    files = {"file": ("admin_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    r = client.post(
        "/api/realtime/batches",
        files=files,
        cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["filename"] == "admin_batch.csv"


def _upload_as(email, role, portal_role, filename):
    """Sign in as a freshly created account and upload one RealTime batch."""
    import io, uuid
    db = TestingSession()
    db.add(PortalUser(
        email=email, display_name=email, password_hash=hash_password("Whatever123!"),
        role=role, portal_role=portal_role, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": email, "password": "Whatever123!"})
    assert login.status_code == 200
    cookies = {"acrn_demo_session": login.cookies["acrn_demo_session"]}
    csv_content = (
        "MRN,Screening #,Randomization #,Form Title,Form Version,Page Title,Field type,Field Label,Data Input,Data Value,Audit Trails,Export Variable Name\n"
        f"MRN-{uuid.uuid4().hex[:6]},SCR-900,RAND-900,Visit 1,v1.0,Vitals,text,Systolic Blood Pressure,118,118,,SBP\n"
    )
    files = {"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    return client.post("/api/realtime/batches", files=files, cookies=cookies), cookies


def test_realtime_session_adjudicator_cannot_upload_or_browse_batches(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r, cookies = _upload_as("sso.upload.adjudicator@acrnhealth.com", "ADJUDICATOR", None, "adjudicator_batch.csv")
    assert r.status_code == 403, r.text
    assert client.get("/api/realtime/batches", cookies=cookies).status_code == 403


def test_realtime_session_chairperson_cannot_upload_or_browse_batches(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r, cookies = _upload_as("sso.upload.chair@acrnhealth.com", "CHAIRPERSON", None, "chair_batch.csv")
    assert r.status_code == 403, r.text
    assert client.get("/api/realtime/batches", cookies=cookies).status_code == 403


def test_realtime_unprovisioned_monitor_cannot_upload_or_view(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r, cookies = _upload_as("sso.upload.monitor.noportal@acrnhealth.com", "MONITOR", None, "noportal_batch.csv")
    assert r.status_code == 403, r.text
    assert client.get("/api/realtime/patients", cookies=cookies).status_code == 403
    assert client.post(QC_DECISION, cookies=cookies).status_code == 403


def test_realtime_adjudicator_cannot_browse_monitor_patient_inventory(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r, cookies = _upload_as("sso.view.adjudicator@acrnhealth.com", "ADJUDICATOR", None, "view_batch.csv")
    assert r.status_code == 403, r.text
    assert client.get("/api/realtime/patients", cookies=cookies).status_code == 403
    assert client.post(QC_DECISION, cookies=cookies).status_code == 403


def test_realtime_qc_decisions_still_reachable_for_monitor_authority(monkeypatch):
    """Guards the QC_DECISION probe: 403 above must mean 'no authority', not 'bad URL'."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    _, cookies = _upload_as("qc.authority@acrnhealth.com", "MONITOR", "MONITOR_QC_REVIEWER", "qc_batch.csv")
    assert client.post(QC_DECISION, cookies=cookies).status_code == 404


def test_realtime_import_still_requires_authentication(monkeypatch):
    """Opening the import to all roles must not open it to anonymous callers.

    Uses its own TestClient: the module-level one carries a cookie jar that earlier
    sign-ins have already populated, so it is not actually anonymous."""
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    anon = TestClient(app)
    assert anon.get("/api/realtime/batches").status_code == 401
    assert anon.post(
        "/api/realtime/batches",
        files={"file": ("anon.csv", b"MRN,Screening #\n1,2\n", "text/csv")},
    ).status_code == 401


def test_realtime_monitor_patient_inventory_enforces_study_scope(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    email = "scoped.monitor@acrnhealth.com"
    db = TestingSession()
    db.add(PortalUser(
        email=email, display_name="Scoped Monitor", password_hash=hash_password("Whatever123!"),
        role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE, study_scope="STUDY-A",
    ))
    batch = RTImportBatch(
        filename="scope.csv", checksum=uuid.uuid4().hex, file_size=1, uploaded_by=email,
        status="MONITOR_QC_REQUIRED",
    )
    db.add(batch)
    db.flush()
    in_scope = LongitudinalParticipant(
        blinded_subject_id=f"SCOPE-A-{uuid.uuid4().hex[:8]}", study="STUDY-A",
        source_batch_id=batch.id, workflow_status="MONITOR_QC_REQUIRED",
    )
    out_of_scope = LongitudinalParticipant(
        blinded_subject_id=f"SCOPE-B-{uuid.uuid4().hex[:8]}", study="STUDY-B",
        source_batch_id=batch.id, workflow_status="MONITOR_QC_REQUIRED",
    )
    db.add_all([in_scope, out_of_scope])
    db.commit()
    out_of_scope_id = out_of_scope.id
    db.close()

    login = client.post("/api/auth/login", json={"email": email, "password": "Whatever123!"})
    cookies = {"acrn_demo_session": login.cookies["acrn_demo_session"]}
    listing = client.get("/api/realtime/patients?include_rejected=true", cookies=cookies)
    assert listing.status_code == 200
    assert {item["study"] for item in listing.json()["items"]} == {"STUDY-A"}
    assert client.get(f"/api/realtime/patients/{out_of_scope_id}", cookies=cookies).status_code == 404


def test_realtime_reviewer_responses_do_not_disclose_peer_identity(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    reviewer_email = "isolated.reviewer@acrnhealth.com"
    peer_email = "hidden.peer@acrnhealth.com"
    db = TestingSession()
    db.add(PortalUser(
        email=reviewer_email, display_name="Isolated Reviewer", password_hash=hash_password("Whatever123!"),
        role="ADJUDICATOR", status=ACTIVE, study_scope="STUDY-PRIVATE",
    ))
    batch = RTImportBatch(
        filename="reviewer-scope.csv", checksum=uuid.uuid4().hex, file_size=1, uploaded_by="monitor",
        status="AUTO_QC_COMPLETE",
    )
    db.add(batch)
    db.flush()
    participant = LongitudinalParticipant(
        blinded_subject_id=f"PRIVATE-{uuid.uuid4().hex[:8]}", study="STUDY-PRIVATE",
        source_batch_id=batch.id, workflow_status="ASSIGNED",
    )
    db.add(participant)
    db.flush()
    db.add_all([
        ReviewerAssignment(participant_id=participant.id, reviewer_upn=reviewer_email, reviewer_role="REVIEWER_A"),
        ReviewerAssignment(participant_id=participant.id, reviewer_upn=peer_email, reviewer_role="REVIEWER_B"),
    ])
    db.commit()
    participant_id = participant.id
    subject_id = participant.blinded_subject_id
    db.close()

    login = client.post("/api/auth/login", json={"email": reviewer_email, "password": "Whatever123!"})
    cookies = {"acrn_demo_session": login.cookies["acrn_demo_session"]}
    queue = client.get("/api/realtime/assigned", cookies=cookies)
    assert queue.status_code == 200
    own_case = next(item for item in queue.json() if item["id"] == str(participant_id))
    assert "assignments" not in own_case

    detail = client.get(f"/api/realtime/assigned/{participant_id}", cookies=cookies)
    assert detail.status_code == 200
    assert "assignments" not in detail.json()

    progress = client.get("/api/realtime/progress", cookies=cookies)
    assert progress.status_code == 200
    own_progress = next(item for item in progress.json()["items"] if item["subject_id"] == subject_id)
    assert own_progress["adjudicators"] == [reviewer_email]
    assert peer_email not in progress.text

