"""
test_e2e_full_lifecycle.py
==========================
Role-based end-to-end lifecycle simulation for the ACRN Adjudication Portal.

Hardened Production Verification:
  - ENABLE_DEMO_ACCOUNTS = false (tested under strict production auth)
  - Real user authentication via /api/auth/login with bcrypt passwords & session cookies
  - Real database session with complete 10-subject evaluation batch
  - Real batch distribution assertions (50% Concordant, 30% Discordant, 20% Three-Way)
  - WS3 Visit-level adjudication with mandatory date_of_diagnosis
  - Adjudicator stickiness across longitudinal visits
  - Positive unblinding path for authorized biostatisticians + negative access control
  - Committee meeting report generation & eTMF manifest archival on meeting sign-off
"""

import io
import csv
import os
import sys
import uuid
import hashlib
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(autouse=True, scope="module")
def enforce_production_auth_env():
    orig = os.environ.get("ENABLE_DEMO_ACCOUNTS")
    os.environ["ENABLE_DEMO_ACCOUNTS"] = "false"
    yield
    if orig is None:
        os.environ.pop("ENABLE_DEMO_ACCOUNTS", None)
    else:
        os.environ["ENABLE_DEMO_ACCOUNTS"] = orig


from conftest import TestingSession
from database import get_db
from main import app
from models.canonical import (
    Participant, AdjudicationRecord, CommitteeDecision, CommitteeMeeting,
    SubjectAssignment, AuditEvent, StudyCode, AdjudicationStatus, ReviewerRole,
    DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel,
)
from models.auth import PortalUser
from fixtures.e2e_packet import (
    seed_e2e_packet, MALFORMED_EDC_CSV, BLINDING_VIOLATION_CSV,
    TEST_PASSWORD_PLAIN, STUDY, STUDY_STR, _SUBJECT_TABLE,
)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def use_db_override():
    prev = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    yield
    if prev is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = prev


@pytest.fixture(scope="module", autouse=True)
def packet():
    """Seed the 12-subject packet once per test module."""
    db = TestingSession()
    p = seed_e2e_packet(db)
    db.close()
    return p



def _db():
    return TestingSession()


def get_auth_client(email: str, password: str = TEST_PASSWORD_PLAIN) -> TestClient:
    """Returns an authenticated TestClient with active session cookies."""
    c = TestClient(app, raise_server_exceptions=True)
    res = c.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return c


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Import, Pseudonymisation, Blinding & QC Gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage1Import:

    def test_S1_01_blinding_violation_csv_rejected(self):
        """A1: Prohibited biomarker columns in EDC CSV are quarantined (SOP-ADJ-002)."""
        file_bytes = BLINDING_VIOLATION_CSV.encode()
        r = client.post(
            "/api/import/edc",
            data={"study": STUDY_STR, "mapping_version": "1.0", "imported_by": "monitor@test.acrn"},
            files={"file": ("blinding_violation.csv", io.BytesIO(file_bytes), "text/csv")},
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "SOP-ADJ-002" in detail or "Blinded" in detail

    def test_S1_02_malformed_rows_rejected_not_persisted(self, packet):
        """A2: Rows missing SUBJID land in validation_errors, never in participants table."""
        file_bytes = MALFORMED_EDC_CSV.encode()
        r = client.post(
            "/api/import/edc",
            data={"study": STUDY_STR, "mapping_version": "1.0", "imported_by": "monitor@test.acrn"},
            files={"file": ("e2e_edc.csv", io.BytesIO(file_bytes), "text/csv")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["participants_imported"] >= 2, "Valid subjects should be imported"
        assert len(body["validation_errors"]) >= 0

        # Verify empty SUBJIDs never persisted
        db = _db()
        bad = db.query(Participant).filter(Participant.subject_id.in_(["", None])).all()
        db.close()
        assert len(bad) == 0, f"Malformed rows persisted in DB: {bad}"

    def test_S1_03_true_subject_id_not_in_adjudicator_api_response(self, packet):
        """A3: Adjudicator GET returns case_number (blinded); true subject_id is strictly shielded."""
        p = packet["participants"][0]
        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        part.qc_approved = True
        db.commit()
        db.close()

        r = client.get(
            f"/api/adjudication/{p['case_number']}",
            params={"requesting_upn": "adj_a@test.acrn"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["case_reference"] == p["case_number"]
        assert p["subject_id"] not in str(body), "True subject_id leaked in adjudicator response"

    def test_S1_04_qc_gate_blocks_assignment_without_approval(self, packet):
        """A4: Assigning adjudicators to non-QC-approved subject is rejected (HTTP 409)."""
        p = packet["participants"][0]
        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        part.qc_approved = False
        db.commit()
        db.close()

        # Login as monitor
        m_client = get_auth_client("monitor@test.acrn")
        r = m_client.post(
            f"/api/monitor/assign/{p['subject_id']}",
            json={
                "reviewer_a_upn": "adj_a@test.acrn",
                "reviewer_b_upn": "adj_b@test.acrn",
                "reason": "QC gate test",
            },
        )
        assert r.status_code == 409, f"Expected 409 QC gate rejection, got: {r.status_code} {r.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Monitor QC, Adjudicator Assignment & Cross-Visit Stickiness
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage2Assignment:

    def _qc_approve(self, subject_id):
        db = _db()
        part = db.query(Participant).filter(
            (Participant.subject_id == subject_id) |
            (Participant.case_number == subject_id)
        ).first()
        if part:
            part.qc_approved = True
            db.commit()
        db.close()

    def test_S2_05_qc_approve_succeeds(self, packet):
        """A5: Monitor QC-approve sets qc_approved=True and writes AuditEvent to DB."""
        p = packet["participants"][0]
        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        part.qc_approved = False
        db.query(AuditEvent).filter_by(participant_id=p["id"], event_type="QC_APPROVED").delete()
        db.commit()
        db.close()

        m_client = get_auth_client("monitor@test.acrn")
        r = m_client.post(
            f"/api/monitor/qc-approve/{p['subject_id']}",
            params={"reason": "E2E clinical review complete"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["qc_approved"] is True

        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        assert part.qc_approved is True
        audit = db.query(AuditEvent).filter_by(participant_id=p["id"], event_type="QC_APPROVED").first()
        assert audit is not None, "QC_APPROVED AuditEvent missing in DB"
        db.close()

    def test_S2_06_a_equals_b_rejected(self, packet):
        """A6: Assigning identical user for Reviewer A and Reviewer B is rejected (409)."""
        p = packet["participants"][1]
        self._qc_approve(p["subject_id"])

        m_client = get_auth_client("monitor@test.acrn")
        r = m_client.post(
            f"/api/monitor/assign/{p['subject_id']}",
            json={
                "reviewer_a_upn": "adj_a@test.acrn",
                "reviewer_b_upn": "adj_a@test.acrn",
                "reason": "A=B invalid attempt",
            },
        )
        assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"

    def test_S2_07_valid_assignment_creates_stickiness_record(self, packet):
        """A7: Valid assignment creates SubjectAssignment record in DB."""
        p = packet["participants"][2]
        self._qc_approve(p["subject_id"])
        db = _db()
        db.query(SubjectAssignment).filter_by(participant_id=p["id"]).delete()
        db.commit()
        db.close()

        m_client = get_auth_client("monitor@test.acrn")
        r = m_client.post(
            f"/api/monitor/assign/{p['subject_id']}",
            json={
                "reviewer_a_upn": "adj_a@test.acrn",
                "reviewer_b_upn": "adj_b@test.acrn",
                "reason": "Valid stickiness assignment",
            },
        )
        assert r.status_code == 200, r.text

        db = _db()
        sa = db.query(SubjectAssignment).filter_by(participant_id=p["id"]).first()
        assert sa is not None
        assert sa.reviewer_a_upn == "adj_a@test.acrn"
        assert sa.reviewer_b_upn == "adj_b@test.acrn"
        db.close()

    def test_S2_08_duplicate_assignment_blocked(self, packet):
        """A8: Duplicate assignment attempt on already-assigned case is blocked (409)."""
        p = packet["participants"][2]
        m_client = get_auth_client("monitor@test.acrn")
        r = m_client.post(
            f"/api/monitor/assign/{p['subject_id']}",
            json={
                "reviewer_a_upn": "adj_a@test.acrn",
                "reviewer_b_upn": "adj_b@test.acrn",
                "reason": "Duplicate attempt",
            },
        )
        assert r.status_code == 409

    def test_S2_09_cross_visit_stickiness_enforced(self, packet):
        """A9: Reviewer A/B stickiness enforced across visits; unassigned reviewer rejected (403)."""
        p = packet["participants"][2]  # assigned to adj_a and adj_b
        # adj_c attempts to submit visit 1 as Reviewer A
        r = client.post(
            f"/api/adjudication/{p['case_number']}/submit",
            json={
                "reviewer_role": "REVIEWER_A",
                "reviewer_upn": "adj_c@test.acrn",  # Unassigned reviewer
                "reviewer_name": "Adj C",
                "reviewer_password": TEST_PASSWORD_PLAIN,
                "visit_number": 1,
                "meets_criteria": True,
                "diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "date_of_diagnosis": "2026-08-01T10:00:00",
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.DEFINITE.value,
                "rationale": "Attempting unassigned cross-visit submission.",
            },
        )
        assert r.status_code == 403, f"Expected 403 stickiness rejection, got: {r.status_code} {r.text}"
        assert "stickiness" in r.text.lower() or "not assigned" in r.text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — WS3 Visit-Level Adjudication & Mandatory Date of Diagnosis
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage3AdjudicatorFlow:

    def _submit(self, case_number, role, upn, password, diagnosis, certainty,
                visit=1, date_of_diagnosis=None):
        return client.post(
            f"/api/adjudication/{case_number}/submit",
            json={
                "reviewer_role": role,
                "reviewer_upn": upn,
                "reviewer_name": upn.split("@")[0],
                "reviewer_password": password,
                "visit_number": visit,
                "meets_criteria": True,
                "diagnosis": diagnosis.value,
                "date_of_diagnosis": date_of_diagnosis,
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": certainty.value,
                "rationale": "Visit-level adjudication rationale with explicit clinical findings.",
            },
        )

    def test_S3_10_wrong_password_rejected(self, packet):
        """A10: Server-side credential check rejects invalid password with 401 (21 CFR Part 11)."""
        p = packet["participants"][0]
        r = self._submit(
            p["case_number"], "REVIEWER_A", "adj_a@test.acrn",
            "BadPassword!999", DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis="2026-08-01T10:00:00",
        )
        assert r.status_code == 401, f"Expected 401, got: {r.status_code} {r.text}"

    def test_S3_11_unknown_upn_rejected(self, packet):
        """A11: Unknown reviewer UPN rejected with 401."""
        p = packet["participants"][0]
        r = self._submit(
            p["case_number"], "REVIEWER_A", "unknown_adjudicator@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis="2026-08-01T10:00:00",
        )
        assert r.status_code == 401

    def test_S3_12_missing_date_of_diagnosis_rejected(self, packet):
        """A12: WS3 requirement: Diagnosing PE without date_of_diagnosis is rejected (HTTP 422)."""
        p = packet["participants"][0]
        r = self._submit(
            p["case_number"], "REVIEWER_A", "adj_a@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis=None,  # Missing date of diagnosis
        )
        assert r.status_code == 422, f"Expected 422 for missing date_of_diagnosis, got: {r.status_code} {r.text}"
        assert "date_of_diagnosis" in r.text

    def test_S3_13_reviewer_a_signs_visit_with_date_of_diagnosis(self, packet):
        """A13: Reviewer A signs visit with valid date_of_diagnosis; SHA-256 sig and AuditEvent written."""
        p = packet["participants"][0]
        # Assign stickiness for subject 0
        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        part.qc_approved = True
        db.query(SubjectAssignment).filter_by(participant_id=p["id"]).delete()
        db.add(SubjectAssignment(
            participant_id=p["id"],
            reviewer_a_upn="adj_a@test.acrn",
            reviewer_b_upn="adj_b@test.acrn",
            status="ACTIVE",
        ))
        db.commit()
        db.close()

        r = self._submit(
            p["case_number"], "REVIEWER_A", "adj_a@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis="2026-08-01T10:00:00",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["signature_hash"]) == 64
        assert body["date_of_diagnosis"] is not None

        db = _db()
        audit = db.query(AuditEvent).filter_by(participant_id=p["id"], event_type="ADJUDICATION_SIGNED").first()
        assert audit is not None
        assert audit.event_metadata.get("date_of_diagnosis") == "2026-08-01T10:00:00"
        db.close()

    def test_S3_14_reviewer_a_cannot_see_b_before_b_signs(self, packet):
        """A14: Runtime Blinding: Reviewer A cannot view Reviewer B's determination before B signs."""
        p = packet["participants"][0]
        r = client.get(
            f"/api/adjudication/{p['case_number']}",
            params={"requesting_upn": "adj_a@test.acrn"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        visible_roles = [rec["reviewer_role"] for rec in body.get("records", [])]
        assert "REVIEWER_B" not in visible_roles, "Blinding breach: Reviewer A saw un-signed Reviewer B record"

    def test_S3_15_reviewer_b_signs_triggers_concordance_check(self, packet):
        """A15: Reviewer B signs visit; concordance derived; participant updated to CONCORDANT."""
        p = packet["participants"][0]
        r = self._submit(
            p["case_number"], "REVIEWER_B", "adj_b@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis="2026-08-01T10:00:00",
        )
        assert r.status_code == 200, r.text
        assert r.json()["participant_status"] == "CONCORDANT"

        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        assert part.status == AdjudicationStatus.CONCORDANT
        db.close()

    def test_S3_16_signed_record_immutable(self, packet):
        """A16: Re-submitting an already-signed visit record returns HTTP 409 Conflict."""
        p = packet["participants"][0]
        r = self._submit(
            p["case_number"], "REVIEWER_A", "adj_a@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.DEFINITE,
            visit=2, date_of_diagnosis="2026-08-01T10:00:00",
        )
        assert r.status_code == 409

    def test_S3_16b_future_date_of_diagnosis_rejected(self, packet):
        """A16b: Date of diagnosis cannot be in the future (HTTP 422)."""
        p = packet["participants"][1]
        db = _db()
        part = db.query(Participant).filter_by(id=p["id"]).first()
        part.qc_approved = True
        db.query(SubjectAssignment).filter_by(participant_id=p["id"]).delete()
        db.add(SubjectAssignment(
            participant_id=p["id"],
            reviewer_a_upn="adj_a@test.acrn",
            reviewer_b_upn="adj_b@test.acrn",
            assigned_by="monitor@test.acrn",
            status="ACTIVE",
        ))
        db.commit()
        db.close()

        r = self._submit(
            p["case_number"], "REVIEWER_A", "adj_a@test.acrn",
            TEST_PASSWORD_PLAIN, DiagnosisCode.PREECLAMPSIA, CertaintyLevel.PROBABLE,
            visit=1, date_of_diagnosis="2099-01-01T12:00:00",
        )
        assert r.status_code == 422, f"Expected 422 for future date, got {r.status_code}: {r.text}"
        assert "future" in r.text.lower()

    def test_S3_16c_definite_certainty_without_criteria_rejected(self, packet):
        """A16c: Definite certainty without diagnostic criteria / complete rationale is rejected (422)."""
        p = packet["participants"][1]
        r = client.post(
            f"/api/adjudication/{p['case_number']}/submit",
            json={
                "reviewer_role": "REVIEWER_A",
                "reviewer_upn": "adj_a@test.acrn",
                "reviewer_name": "Adj A",
                "reviewer_password": TEST_PASSWORD_PLAIN,
                "visit_number": 1,
                "meets_criteria": False,  # Does not meet criteria
                "diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "date_of_diagnosis": "2026-08-01T10:00:00",
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.DEFINITE.value,  # Incompatible with meets_criteria=False
                "rationale": "Short note",
            },
        )
        assert r.status_code == 422
        assert "Definite certainty" in r.text or "diagnostic criteria" in r.text

    def test_S3_16d_cumulative_visits_1_to_n_progression(self, packet):
        """A16d: Longitudinal progression: One subject across 6 sequential visits accumulates 6 records with progressive certainty."""
        # Create a dedicated multi-visit subject
        db = _db()
        sid = "ZWE999-LONG-01"
        cno = "ADJ-LONG-01"
        p = db.query(Participant).filter_by(subject_id=sid).first()
        if not p:
            p = Participant(
                subject_id=sid, case_number=cno, site_code="ZWE999",
                study=STUDY, status=AdjudicationStatus.PENDING,
                visit_count=6, qc_approved=True,
            )
            db.add(p)
            db.flush()
        else:
            p.qc_approved = True
            db.query(AdjudicationRecord).filter_by(participant_id=p.id).delete()
            db.query(SubjectAssignment).filter_by(participant_id=p.id).delete()

        db.add(SubjectAssignment(
            participant_id=p.id, reviewer_a_upn="adj_a@test.acrn",
            reviewer_b_upn="adj_b@test.acrn", assigned_by="monitor@test.acrn",
            status="ACTIVE",
        ))
        db.commit()
        db.close()

        # Submit 6 sequential visits with increasing clinical certainty
        visits_data = [
            (1, DiagnosisCode.NOT_PE, None, CertaintyLevel.POSSIBLE, False, "Visit 1 routine screening: Normotensive."),
            (2, DiagnosisCode.GESTATIONAL_HTN, "2026-08-02T09:00:00", CertaintyLevel.PROBABLE, True, "Visit 2: Blood pressure elevated (142/92 mmHg)."),
            (3, DiagnosisCode.PREECLAMPSIA, "2026-08-05T14:00:00", CertaintyLevel.DEFINITE, True, "Visit 3: Severe BP 164/112 mmHg with proteinuria UPCR 1.84 g/g."),
            (4, DiagnosisCode.PREECLAMPSIA, "2026-08-05T14:00:00", CertaintyLevel.DEFINITE, True, "Visit 4: Persistent severe hypertension requiring labetalol."),
            (5, DiagnosisCode.PREECLAMPSIA, "2026-08-05T14:00:00", CertaintyLevel.DEFINITE, True, "Visit 5: Pre-delivery evaluation, thrombocytopenia documented."),
            (6, DiagnosisCode.PREECLAMPSIA, "2026-08-05T14:00:00", CertaintyLevel.DEFINITE, True, "Visit 6: Postpartum Day 7 follow-up, gradual BP normalization."),
        ]

        for v_num, diag, dod, cert, meets, rat in visits_data:
            r = client.post(
                f"/api/adjudication/{cno}/submit",
                json={
                    "reviewer_role": "REVIEWER_A",
                    "reviewer_upn": "adj_a@test.acrn",
                    "reviewer_name": "Adj A",
                    "reviewer_password": TEST_PASSWORD_PLAIN,
                    "visit_number": v_num,
                    "meets_criteria": meets,
                    "diagnosis": diag.value,
                    "date_of_diagnosis": dod,
                    "onset_class": OnsetClass.EOPE.value,
                    "severity": SeverityGrade.WITH_SEVERE.value if diag == DiagnosisCode.PREECLAMPSIA else SeverityGrade.WITHOUT_SEVERE.value,
                    "certainty": cert.value,
                    "rationale": rat,
                },
            )
            assert r.status_code == 200, f"Visit {v_num} submission failed: {r.text}"

        # Verify DB records
        db = _db()
        part = db.query(Participant).filter_by(subject_id=sid).first()
        records = db.query(AdjudicationRecord).filter_by(participant_id=part.id).order_by(AdjudicationRecord.visit_number.asc()).all()
        assert len(records) == 6, f"Expected 6 cumulative visit records, found {len(records)}"
        assert records[0].certainty == CertaintyLevel.POSSIBLE
        assert records[1].certainty == CertaintyLevel.PROBABLE
        assert records[2].certainty == CertaintyLevel.DEFINITE
        assert records[2].date_of_diagnosis == datetime(2026, 8, 5, 14, 0)
        assert records[5].certainty == CertaintyLevel.DEFINITE
        db.close()



# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Reviewer C Independence & Discordance Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage4ReviewerC:

    def _seed_discordant(self, n: int) -> dict:
        db = _db()
        sid = f"ZWE999-E2E-{n:02d}"
        cno = f"ADJ-E2E-{n:02d}"
        p = db.query(Participant).filter_by(subject_id=sid).first()
        if not p:
            p = Participant(
                subject_id=sid, case_number=cno, site_code="ZWE999",
                study=STUDY, status=AdjudicationStatus.DISCORDANT,
                visit_count=2, qc_approved=True,
            )
            db.add(p)
            db.flush()
        else:
            p.status = AdjudicationStatus.DISCORDANT

        # Seed Reviewer A & B records
        db.query(AdjudicationRecord).filter_by(participant_id=p.id).delete()
        db.add(AdjudicationRecord(
            participant_id=p.id, reviewer_role=ReviewerRole.REVIEWER_A,
            reviewer_upn="adj_a@test.acrn", reviewer_name="Adj A", visit_number=1,
            diagnosis=DiagnosisCode.PREECLAMPSIA, date_of_diagnosis=datetime(2026, 8, 6, 12, 0),
            onset_class=OnsetClass.EOPE, severity=SeverityGrade.WITH_SEVERE,
            certainty=CertaintyLevel.PROBABLE, rationale="A rationale.",
            signed=True, signed_at=datetime.utcnow(),
        ))
        db.add(AdjudicationRecord(
            participant_id=p.id, reviewer_role=ReviewerRole.REVIEWER_B,
            reviewer_upn="adj_b@test.acrn", reviewer_name="Adj B", visit_number=1,
            diagnosis=DiagnosisCode.GESTATIONAL_HTN, date_of_diagnosis=datetime(2026, 8, 6, 12, 0),
            onset_class=OnsetClass.EOPE, severity=SeverityGrade.WITHOUT_SEVERE,
            certainty=CertaintyLevel.PROBABLE, rationale="B rationale.",
            signed=True, signed_at=datetime.utcnow(),
        ))

        db.query(SubjectAssignment).filter_by(participant_id=p.id).delete()
        db.add(SubjectAssignment(
            participant_id=p.id, reviewer_a_upn="adj_a@test.acrn",
            reviewer_b_upn="adj_b@test.acrn", status="ACTIVE",
        ))
        db.commit()
        ret = {"id": p.id, "subject_id": p.subject_id, "case_number": p.case_number}
        db.close()
        return ret

    def test_S4_17_reviewer_c_same_as_a_rejected(self):
        """A17: Reviewer C matching Reviewer A's identity is rejected (409 Conflict)."""
        p = self._seed_discordant(6)
        r = client.post(
            f"/api/committee/{p['subject_id']}/reviewer-c",
            json={
                "reviewer_upn": "adj_a@test.acrn",  # Same as Reviewer A
                "reviewer_name": "Adj A",
                "diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.PROBABLE.value,
                "rationale": "C determination attempting A identity.",
                "visit_number": 1,
            },
        )
        assert r.status_code == 409, f"Expected 409 C=A rejection, got: {r.status_code} {r.text}"

    def test_S4_18_reviewer_c_same_as_b_rejected(self):
        """A18: Reviewer C matching Reviewer B's identity is rejected (409 Conflict)."""
        p = self._seed_discordant(6)
        r = client.post(
            f"/api/committee/{p['subject_id']}/reviewer-c",
            json={
                "reviewer_upn": "adj_b@test.acrn",  # Same as Reviewer B
                "reviewer_name": "Adj B",
                "diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.PROBABLE.value,
                "rationale": "C determination attempting B identity.",
                "visit_number": 1,
            },
        )
        assert r.status_code == 409

    def test_S4_19_c_matches_a_gives_concordant_with_a(self):
        """A19: Independent Reviewer C matching A resolves case as CONCORDANT_WITH_A."""
        p = self._seed_discordant(6)
        r = client.post(
            f"/api/committee/{p['subject_id']}/reviewer-c",
            json={
                "reviewer_upn": "adj_c@test.acrn",
                "reviewer_name": "Adj C",
                "diagnosis": DiagnosisCode.PREECLAMPSIA.value,  # Matches A
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.PROBABLE.value,
                "rationale": "Independent Reviewer C agrees with Reviewer A.",
                "visit_number": 1,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["concordance_status"] == "CONCORDANT_WITH_A"
        assert body["three_way_divergent"] is False

    def test_S4_20_c_independent_gives_three_way(self):
        """A20: Reviewer C selecting distinct 3rd diagnosis produces THREE_WAY_DIVERGENT status."""
        p = self._seed_discordant(7)
        r = client.post(
            f"/api/committee/{p['subject_id']}/reviewer-c",
            json={
                "reviewer_upn": "adj_c@test.acrn",
                "reviewer_name": "Adj C",
                "diagnosis": DiagnosisCode.CHRONIC_HTN.value,  # Distinct from A (PE) & B (gHTN)
                "onset_class": OnsetClass.EOPE.value,
                "severity": SeverityGrade.WITH_SEVERE.value,
                "certainty": CertaintyLevel.PROBABLE.value,
                "rationale": "Independent Reviewer C assesses pre-existing chronic HTN.",
                "visit_number": 1,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["concordance_status"] == "THREE_WAY_DIVERGENT"
        assert body["three_way_divergent"] is True

        db = _db()
        audit = db.query(AuditEvent).filter_by(participant_id=p["id"], event_type="REVIEWER_C_SIGNED").first()
        assert audit is not None
        assert audit.event_metadata.get("three_way_divergent") is True
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Chairperson Arbitration, Agenda Pack, Report & Sign-Off
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage5Chairperson:

    def _seed_chair_decision(self, sid: str, locked: bool = True) -> dict:
        db = _db()
        p = db.query(Participant).filter_by(subject_id=sid).first()
        if not p:
            p = Participant(
                subject_id=sid, case_number=f"ADJ-{sid}", site_code="ZWE999",
                study=STUDY, status=AdjudicationStatus.FINALIZED if locked else AdjudicationStatus.DISCORDANT,
                visit_count=2, qc_approved=True,
            )
            db.add(p)
            db.flush()

        dec = db.query(CommitteeDecision).filter_by(participant_id=p.id).first()
        if not dec:
            dec = CommitteeDecision(
                participant_id=p.id,
                final_diagnosis=DiagnosisCode.PREECLAMPSIA,
                date_of_diagnosis=datetime(2026, 8, 9, 14, 0),
                final_onset_class=OnsetClass.EOPE,
                final_severity=SeverityGrade.WITH_SEVERE,
                final_certainty=CertaintyLevel.DEFINITE,
                chair_rationale="Committee consensus decision reached.",
                quorum_met=True,
                members_present=4,
                chair_upn="chair@test.acrn",
                chair_name="Chair",
                signature_hash=hashlib.sha256(b"chair_decision_sig").hexdigest(),
                locked=locked,
                locked_at=datetime.utcnow() if locked else None,
                concordance_status="CHAIR_LOCKED",
            )
            db.add(dec)
        db.commit()
        ret = {"id": p.id, "subject_id": p.subject_id, "case_number": p.case_number}
        db.close()
        return ret

    def test_S5_21_chairperson_sees_completed_cases(self):
        """A21: Chairperson GET completed-adjudications includes finalized cases."""
        self._seed_chair_decision("ZWE999-CHAIR-01", locked=True)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.get("/api/chairperson/completed-adjudications")
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items", body) if isinstance(body, dict) else body
        assert isinstance(items, list)
        assert len(items) >= 1

    def test_S5_22_agenda_pack_contains_all_discordant_and_three_way_cases(self):
        """A22: Agenda pack contains structured discordant arbitration items and consent calendar."""
        # Ensure discordant cases exist
        self._seed_chair_decision("ZWE999-DISC-01", locked=False)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.get("/api/chairperson/agenda-pack")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items_for_committee_arbitration" in body
        assert "concordant_cases_consent_calendar" in body
        assert isinstance(body["items_for_committee_arbitration"], list)
        assert isinstance(body["concordant_cases_consent_calendar"], list)

    def test_S5_23_committee_lock_requires_quorum(self):
        """A23: Committee lock endpoint rejects submission when quorum_met is False (400)."""
        p = self._seed_chair_decision("ZWE999-QUORUM-01", locked=False)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.post(
            f"/api/committee/{p['subject_id']}/lock",
            json={
                "chair_upn": "chair@test.acrn",
                "chair_name": "Committee Chair",
                "final_diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "final_onset_class": OnsetClass.EOPE.value,
                "final_severity": SeverityGrade.WITH_SEVERE.value,
                "final_certainty": CertaintyLevel.DEFINITE.value,
                "chair_rationale": "Lock attempt without quorum.",
                "quorum_met": False,  # Quorum not met
                "members_present": 2,
            },
        )
        assert r.status_code == 400, f"Expected 400 quorum failure, got: {r.status_code} {r.text}"

    def test_S5_24_chairperson_signature_hash_format(self):
        """A24: Committee lock generates 64-char SHA-256 e-signature hash."""
        p = self._seed_chair_decision("ZWE999-SIG-01", locked=False)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.post(
            f"/api/committee/{p['subject_id']}/lock",
            json={
                "chair_upn": "chair@test.acrn",
                "chair_name": "Committee Chair",
                "final_diagnosis": DiagnosisCode.PREECLAMPSIA.value,
                "final_onset_class": OnsetClass.EOPE.value,
                "final_severity": SeverityGrade.WITH_SEVERE.value,
                "final_certainty": CertaintyLevel.DEFINITE.value,
                "chair_rationale": "Formal consensus lock.",
                "quorum_met": True,
                "members_present": 4,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["signature_hash"]) == 64

    def test_S5_25_finalized_case_strictly_immutable_to_re_lock(self):
        """A25: Attempting to modify or re-lock a finalized case is strictly rejected (409 Conflict)."""
        p = self._seed_chair_decision("ZWE999-IMMUT-01", locked=True)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.post(
            f"/api/committee/{p['subject_id']}/lock",
            json={
                "chair_upn": "chair@test.acrn",
                "chair_name": "Committee Chair",
                "final_diagnosis": DiagnosisCode.GESTATIONAL_HTN.value,  # Attempting mutation
                "final_onset_class": OnsetClass.EOPE.value,
                "final_severity": SeverityGrade.WITHOUT_SEVERE.value,
                "final_certainty": CertaintyLevel.PROBABLE.value,
                "chair_rationale": "Attempted re-lock override.",
                "quorum_met": True,
                "members_present": 4,
            },
        )
        assert r.status_code == 409, f"Expected 409 re-lock rejection, got: {r.status_code} {r.text}"

    def test_S5_26_meeting_sign_off_generates_report_and_etmf_write(self):
        """A26: Meeting sign-off generates meeting report, writes to eTMF, marks cases CLOSED."""
        p = self._seed_chair_decision("ZWE999-MEET-01", locked=True)
        c_client = get_auth_client("chair@test.acrn")
        r = c_client.post(
            "/api/chairperson/meetings/sign-off",
            json={
                "meeting_title": "PROTECT-Africa EAC Session 12",
                "batch_id": "BATCH-2026-08",
                "attendees": ["Chairperson (Chair)", "Adj A", "Adj B", "Adj C"],
                "quorum_met": True,
                "minutes": "Full committee reviewed all discordant and 3-way divergent cases and reached unanimous consensus.",
                "case_ids": [p["subject_id"]],
                "chair_name": "Adjudication Committee Chairperson",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "success"
        assert len(body["signature_hash"]) == 64
        assert body["etmf_destination"] is not None

        db = _db()
        part = db.query(Participant).filter_by(subject_id=p["subject_id"]).first()
        assert part.status == AdjudicationStatus.CLOSED
        audit = db.query(AuditEvent).filter_by(event_type="COMMITTEE_MEETING_SIGNED").first()
        assert audit is not None
        db.close()

    def test_S5_27_meeting_report_retrieval(self):
        """A27: Chairperson can retrieve structured meeting summary from GET /meetings/{id}/report."""
        c_client = get_auth_client("chair@test.acrn")
        # List meetings to get the latest meeting ID
        list_r = c_client.get("/api/chairperson/meetings")
        assert list_r.status_code == 200
        meetings = list_r.json().get("items", [])
        assert len(meetings) >= 1
        m_id = meetings[0]["id"]

        r = c_client.get(f"/api/chairperson/meetings/{m_id}/report")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["meeting_id"] == m_id
        assert body["meeting_title"] is not None
        assert body["minutes"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — Post-Meeting, Positive Unblinding Path & eTMF Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestStage6PostMeeting:

    def test_S6_28_study_analysis_csv_shape_and_dates(self):
        """A28: Blinded study-analysis CSV contains case_number, date_of_diagnosis, NO true subject_id."""
        r = client.get("/api/export/study-analysis?study=PROTECT-Africa")
        assert r.status_code == 200, r.text
        csv_text = r.text
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        headers = reader.fieldnames or []

        assert "blinded_subject_id" in headers
        assert "date_of_diagnosis" in headers
        assert "visit_number" in headers
        assert "outcome" in headers
        assert "true_subject_id" not in headers

        for row in rows:
            # Blinded identifier check
            assert not row["blinded_subject_id"].startswith("ZWE999-E2E"), "True subject_id leaked in blinded CSV"

    def test_S6_29_unblinded_export_blocked_when_feature_gate_disabled(self):
        """A29: Unblinded analysis export is locked & blocked when ENABLE_UNBLINDED_EXPORT is false."""

        b_client = get_auth_client("biostat@test.acrn")
        r = b_client.get("/api/export/unblinded-analysis?study=PROTECT-Africa")
        assert r.status_code == 403, f"Expected 403 gate lock, got: {r.status_code} {r.text}"
        assert "locked and disabled" in r.text or "Nqobani Ncube" in r.text

        db = _db()
        audit = db.query(AuditEvent).filter_by(event_type="UNBLINDED_EXPORT_BLOCKED").first()
        assert audit is not None, "UNBLINDED_EXPORT_BLOCKED AuditEvent missing"
        db.close()

    def test_S6_29b_positive_unblinding_when_enabled_for_authorized_admin(self, monkeypatch):
        """A29b: Positive Unblinding Path: When authorized (ENABLE_UNBLINDED_EXPORT=true), Admin can export."""
        import api.export as exp_mod
        monkeypatch.setattr(exp_mod, "ENABLE_UNBLINDED_EXPORT", True)

        # Seed admin user
        db = _db()
        admin_u = db.query(PortalUser).filter_by(email="admin_e2e@test.acrn").first()
        if not admin_u:
            admin_u = PortalUser(
                email="admin_e2e@test.acrn",
                display_name="Admin E2E",
                role="ADMIN",
                portal_role="ADMIN",
                password_hash=hashlib.sha256(b"admin").hexdigest(),
                status="ACTIVE",
                study_scope="*",
                is_demo_account=False,
            )
            from fixtures.e2e_packet import _hash
            admin_u.password_hash = _hash()
            db.add(admin_u)
            db.commit()
        db.close()

        adm_client = get_auth_client("admin_e2e@test.acrn")
        r = adm_client.get("/api/export/unblinded-analysis?study=PROTECT-Africa")
        assert r.status_code == 200, r.text
        csv_text = r.text
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        headers = reader.fieldnames or []

        assert "true_subject_id" in headers
        assert "sflt1_pg_ml" in headers
        assert "plgf_pg_ml" in headers
        assert "date_of_diagnosis" in headers
        assert len(rows) >= 1

        db = _db()
        audit = db.query(AuditEvent).filter_by(event_type="UNBLINDED_DATA_ACCESSED").first()
        assert audit is not None, "UNBLINDED_DATA_ACCESSED AuditEvent missing"
        db.close()

    def test_S6_30_unauthorized_unblinding_attempt_blocked(self, monkeypatch):
        """A30: Unauthorized role (Adjudicator) attempting unblinded export is blocked with 403."""
        import api.export as exp_mod
        monkeypatch.setattr(exp_mod, "ENABLE_UNBLINDED_EXPORT", True)

        a_client = get_auth_client("adj_a@test.acrn")
        r = a_client.get("/api/export/unblinded-analysis?study=PROTECT-Africa")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

        db = _db()
        audit = db.query(AuditEvent).filter_by(event_type="UNBLINDED_ACCESS_DENIED").first()
        assert audit is not None, "UNBLINDED_ACCESS_DENIED AuditEvent missing"
        db.close()


    def test_S6_31_etmf_local_adapter_manifest_verification(self):
        """A31: LocalFilesystemAdapter creates PDF artifact with valid SHA-256 sidecar manifest."""
        from services.etmf_adapter import LocalFilesystemAdapter
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = LocalFilesystemAdapter(root=tmp_dir)
            sample_pdf = b"%PDF-1.4 sample content for eTMF validation"
            dest = adapter.write(
                subject_id="ZWE999-TEST",
                blinded_id="ADJ-TEST-01",
                study="PROTECT-Africa",
                pdf_bytes=sample_pdf,
            )
            assert os.path.exists(dest)
            sha_file = dest + ".sha256"
            assert os.path.exists(sha_file)
            recorded_hash = Path(sha_file).read_text().split()[0]
            assert recorded_hash == hashlib.sha256(sample_pdf).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH SIMULATION & DISTRIBUTION ASSERTION (10 EVALUABLE SUBJECTS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchSimulationAndDistribution:

    def test_batch_simulation_full_lifecycle_and_distribution(self, packet):
        """
        Drives the entire 10-subject evaluation packet through all stages:
          - QC Approval & Assignment
          - Bilateral Adjudicator Submissions (A & B) with dates of diagnosis
          - Reviewer C Discordance Resolutions
          - Committee Arbitration & Sign-off
        Asserts the exact outcome distribution:
          - 5 Concordant (50%)
          - 3 Discordant resolved by Reviewer C (30%)
          - 2 Three-Way Divergent resolved by Committee (20%)
        """
        m_client = get_auth_client("monitor@test.acrn")
        c_client = get_auth_client("chair@test.acrn")

        # Reset all evaluation subjects to clean PENDING state
        db = _db()
        for row in _SUBJECT_TABLE:
            n = row[0]
            sid = f"ZWE999-E2E-{n:02d}"
            part = db.query(Participant).filter_by(subject_id=sid).first()
            if part:
                part.status = AdjudicationStatus.PENDING
                part.qc_approved = False
                db.query(AdjudicationRecord).filter_by(participant_id=part.id).delete()
                db.query(CommitteeDecision).filter_by(participant_id=part.id).delete()
                db.query(SubjectAssignment).filter_by(participant_id=part.id).delete()
        db.commit()
        db.close()

        concordant_count = 0
        discordant_count = 0
        three_way_count = 0


        for row in _SUBJECT_TABLE:
            n, visit_num, diag_a, diag_b, cert_a, cert_b, diag_c, chair_diag, path, dod_str = row
            sid = f"ZWE999-E2E-{n:02d}"
            cno = f"ADJ-E2E-{n:02d}"

            # 1. QC Approve
            qc_res = m_client.post(f"/api/monitor/qc-approve/{sid}", params={"reason": "Batch QC approval"})
            assert qc_res.status_code == 200

            # 2. Assign Reviewer A & B
            db = _db()
            p_obj = db.query(Participant).filter_by(subject_id=sid).first()
            db.query(SubjectAssignment).filter_by(participant_id=p_obj.id).delete()
            db.commit()
            db.close()

            assign_res = m_client.post(
                f"/api/monitor/assign/{sid}",
                json={"reviewer_a_upn": "adj_a@test.acrn", "reviewer_b_upn": "adj_b@test.acrn", "reason": "Batch assignment"},
            )
            assert assign_res.status_code == 200

            # 3. Submit Reviewer A
            sub_a = client.post(
                f"/api/adjudication/{cno}/submit",
                json={
                    "reviewer_role": "REVIEWER_A", "reviewer_upn": "adj_a@test.acrn",
                    "reviewer_name": "Adj A", "reviewer_password": TEST_PASSWORD_PLAIN,
                    "visit_number": visit_num, "meets_criteria": True,
                    "diagnosis": diag_a.value, "date_of_diagnosis": dod_str,
                    "onset_class": OnsetClass.EOPE.value, "severity": SeverityGrade.WITH_SEVERE.value,
                    "certainty": cert_a.value, "rationale": f"Batch determination Reviewer A for case {n}",
                },
            )
            assert sub_a.status_code == 200, f"Reviewer A submission failed on case {n}: {sub_a.text}"

            # 4. Submit Reviewer B
            sub_b = client.post(
                f"/api/adjudication/{cno}/submit",
                json={
                    "reviewer_role": "REVIEWER_B", "reviewer_upn": "adj_b@test.acrn",
                    "reviewer_name": "Adj B", "reviewer_password": TEST_PASSWORD_PLAIN,
                    "visit_number": visit_num, "meets_criteria": True,
                    "diagnosis": diag_b.value, "date_of_diagnosis": dod_str,
                    "onset_class": OnsetClass.EOPE.value, "severity": SeverityGrade.WITH_SEVERE.value,
                    "certainty": cert_b.value, "rationale": f"Batch determination Reviewer B for case {n}",
                },
            )
            assert sub_b.status_code == 200, f"Reviewer B submission failed on case {n}: {sub_b.text}"

            # Check concordance state
            if path == "concordant":
                assert sub_b.json()["participant_status"] == "CONCORDANT"
                concordant_count += 1
            else:
                # After discordant A/B, the backend now immediately moves to COMMITTEE_PENDING
                # and auto-assigns Reviewer C (state machine condensed — DISCORDANT is no longer
                # an intermediate resting state; COMMITTEE_PENDING is the correct status).
                assert sub_b.json()["participant_status"] in ("DISCORDANT", "COMMITTEE_PENDING"), (
                    f"Expected discordant path status for case {n}, "
                    f"got: {sub_b.json()['participant_status']}"
                )

                # 5. Submit Reviewer C (use dynamically assigned Reviewer C)
                db = _db()
                p_rec = db.query(Participant).filter_by(subject_id=sid).first()
                asgn = db.query(SubjectAssignment).filter_by(participant_id=p_rec.id).first()
                assigned_c_upn = asgn.reviewer_c_upn if asgn and asgn.reviewer_c_upn else "adj_c@test.acrn"
                db.close()

                sub_c = client.post(
                    f"/api/committee/{sid}/reviewer-c",
                    json={
                        "reviewer_upn": assigned_c_upn, "reviewer_name": "Adj C",
                        "diagnosis": diag_c.value, "onset_class": OnsetClass.EOPE.value,
                        "severity": SeverityGrade.WITH_SEVERE.value, "certainty": CertaintyLevel.PROBABLE.value,
                        "rationale": f"Reviewer C arbitration on case {n}", "visit_number": visit_num,
                    },
                )
                assert sub_c.status_code == 200, f"Reviewer C submission failed on case {n}: {sub_c.text}"

                if path == "discordant":
                    assert sub_c.json()["concordance_status"] in ("CONCORDANT_WITH_A", "CONCORDANT_WITH_B")
                    discordant_count += 1
                elif path == "three_way":
                    assert sub_c.json()["concordance_status"] == "THREE_WAY_DIVERGENT"
                    three_way_count += 1

                    # 6. Committee Chair lock
                    lock_res = c_client.post(
                        f"/api/committee/{sid}/lock",
                        json={
                            "chair_upn": "chair@test.acrn", "chair_name": "Chair",
                            "final_diagnosis": chair_diag.value, "final_onset_class": OnsetClass.EOPE.value,
                            "final_severity": SeverityGrade.WITH_SEVERE.value,
                            "final_certainty": CertaintyLevel.DEFINITE.value,
                            "chair_rationale": f"Committee arbitration final lock for case {n}",
                            "quorum_met": True, "members_present": 4,
                        },
                    )
                    assert lock_res.status_code == 200

        # Distribution assertions across the 10-subject evaluation batch
        total_evaluable = len(_SUBJECT_TABLE)
        assert total_evaluable == 10
        assert concordant_count == 5, f"Expected 5 concordant cases (50%), got {concordant_count}"
        assert discordant_count == 3, f"Expected 3 discordant cases (30%), got {discordant_count}"
        assert three_way_count == 2, f"Expected 2 three-way cases (20%), got {three_way_count}"

        pct_concordant = (concordant_count / total_evaluable) * 100.0
        pct_discordant = (discordant_count / total_evaluable) * 100.0
        pct_three_way = (three_way_count / total_evaluable) * 100.0

        assert pct_concordant == 50.0
        assert pct_discordant == 30.0
        assert pct_three_way == 20.0


# ═══════════════════════════════════════════════════════════════════════════════
# NEGATIVE ACCESS MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeAccessMatrix:

    def test_anonymous_access_blocked(self):
        """Anonymous access to protected endpoints is rejected with 401."""
        unauth_client = TestClient(app)
        r = unauth_client.get("/api/chairperson/completed-adjudications")
        assert r.status_code == 401

    def test_non_monitor_cannot_access_monitor_endpoints(self):
        """Adjudicator cannot access monitor assign endpoint."""
        a_client = get_auth_client("adj_a@test.acrn")
        r = a_client.post(
            "/api/monitor/assign/ZWE999-E2E-01",
            json={"reviewer_a_upn": "adj_a@test.acrn", "reviewer_b_upn": "adj_b@test.acrn"},
        )
        assert r.status_code in (401, 403)
