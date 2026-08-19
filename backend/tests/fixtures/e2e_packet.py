"""
Deterministic 12-subject E2E test packet seeder.
=================================================
Produces a reproducible data set with a known outcome distribution for the
full lifecycle simulation.  All identifiers are synthetic – no real patient data.

Subject distribution
--------------------
ADJ-E2E-01 to 04  : 6 visits each (DV26=100%).  Concordant pairs.   → FINALIZED via CONCORDANT path
ADJ-E2E-05 to 08  : 4 visits each (DV26 incomplete). DV27 capped.   → DISCORDANT → Reviewer C path
ADJ-E2E-09        : 1 visit only                                      → DISCORDANT
ADJ-E2E-10        : 1 visit only                                      → THREE_WAY_DIVERGENT
ADJ-E2E-11, 12    : malformed (no subject_id) — rejected at import   → never inserted as Participant

Outcome distribution (of the 10 valid subjects)
-  6 concordant  (ADJ-E2E-01 to 06)
-  2 discordant  (ADJ-E2E-07, 08)
-  2 three-way   (ADJ-E2E-09, 10)

Seeded users
------------
adj_a@test.acrn    ADJUDICATOR   (Reviewer A)
adj_b@test.acrn    ADJUDICATOR   (Reviewer B)
adj_c@test.acrn    ADJUDICATOR   (Reviewer C — independent)
adj_d@test.acrn    ADJUDICATOR   (spare — not assigned in primary scenario)
chair@test.acrn    CHAIRPERSON
monitor@test.acrn  MONITOR       (ADJUDICATION_COORDINATOR portal_role)
"""

import uuid
from datetime import datetime, timedelta

from models.canonical import (
    Participant, AdjudicationRecord, CommitteeDecision,
    SubjectAssignment, AuditEvent,
    StudyCode, AdjudicationStatus, ReviewerRole,
    DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel,
)
from models.auth import PortalUser
from services.auth_service import hash_password

STUDY = StudyCode.EOPE
STUDY_STR = "PROTECT-Africa"
TEST_PASSWORD_PLAIN = "E2ETestPass@2026"
TEST_PASSWORD_HASH = None   # computed lazily


def _hash():
    global TEST_PASSWORD_HASH
    if TEST_PASSWORD_HASH is None:
        TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD_PLAIN)
    return TEST_PASSWORD_HASH


# ── Seeded users ──────────────────────────────────────────────────────────────

E2E_USERS = [
    {"email": "adj_a@test.acrn", "name": "Adj A",         "role": "ADJUDICATOR", "portal_role": None},
    {"email": "adj_b@test.acrn", "name": "Adj B",         "role": "ADJUDICATOR", "portal_role": None},
    {"email": "adj_c@test.acrn", "name": "Adj C",         "role": "ADJUDICATOR", "portal_role": None},
    {"email": "adj_d@test.acrn", "name": "Adj D",         "role": "ADJUDICATOR", "portal_role": None},
    {"email": "chair@test.acrn", "name": "Chair",         "role": "CHAIRPERSON",  "portal_role": None},
    {"email": "monitor@test.acrn","name": "Monitor",      "role": "MONITOR",
     "portal_role": "ADJUDICATION_COORDINATOR"},
    {"email": "biostat@test.acrn", "name": "Biostatistician", "role": "BIOSTATISTICIAN",
     "portal_role": "BIOSTATISTICIAN"},
]


def seed_e2e_users(db) -> dict[str, PortalUser]:
    """Create or retrieve E2E test user accounts. Returns {email: PortalUser}."""
    from models.auth import CommitteeAssignment
    users = {}
    for u in E2E_USERS:
        existing = db.query(PortalUser).filter_by(email=u["email"]).first()
        if not existing:
            existing = PortalUser(
                email=u["email"],
                display_name=u["name"],
                role=u["role"],
                portal_role=u.get("portal_role"),
                password_hash=_hash(),
                status="ACTIVE",
                study_scope="*",
                is_demo_account=False,
            )
            db.add(existing)
            db.flush()
        else:
            existing.password_hash = _hash()
            existing.status = "ACTIVE"
            existing.portal_role = u.get("portal_role")
            existing.role = u["role"]
            db.flush()

        if u["role"] == "CHAIRPERSON":
            assign = db.query(CommitteeAssignment).filter_by(
                user_id=existing.id, assignment_type="CHAIRPERSON"
            ).first()
            if not assign:
                db.add(CommitteeAssignment(
                    user_id=existing.id,
                    assignment_type="CHAIRPERSON",
                    committee_name="Endpoint Adjudication Committee",
                    is_active=True,
                    status="ACTIVE",
                ))
    db.flush()
    for u in E2E_USERS:
        users[u["email"]] = db.query(PortalUser).filter_by(email=u["email"]).first()
    return users


# ── Subject data table ────────────────────────────────────────────────────────

def _subject(n: int, visit_count: int) -> dict:
    sid = f"ZWE999-E2E-{n:02d}"
    cno = f"ADJ-E2E-{n:02d}"
    return {"subject_id": sid, "case_number": cno, "visit_count": visit_count}


# Subject index → (n, visit_number, A diag, B diag, A certainty, B certainty, C diag, Chair diag, path, dod_str)
# Outcome distribution (10 evaluable subjects):
# 5 Concordant (50%): Cases 1-5
# 3 Discordant (30%): Cases 6-8 (resolved by Reviewer C)
# 2 Three-Way (20%): Cases 9-10 (arbitrated & locked by Committee Chair)
_SUBJECT_TABLE = [
    (1,  2, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.PREECLAMPSIA,     CertaintyLevel.DEFINITE,  CertaintyLevel.DEFINITE,  None,                         None,                         "concordant", "2026-08-01T10:00:00"),
    (2,  1, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.PREECLAMPSIA,     CertaintyLevel.DEFINITE,  CertaintyLevel.DEFINITE,  None,                         None,                         "concordant", "2026-08-02T11:00:00"),
    (3,  3, DiagnosisCode.GESTATIONAL_HTN,  DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  None,                         None,                         "concordant", "2026-08-03T09:30:00"),
    (4,  1, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.PREECLAMPSIA,     CertaintyLevel.DEFINITE,  CertaintyLevel.DEFINITE,  None,                         None,                         "concordant", "2026-08-04T14:15:00"),
    (5,  2, DiagnosisCode.GESTATIONAL_HTN,  DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  None,                         None,                         "concordant", "2026-08-05T08:45:00"),
    (6,  1, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  DiagnosisCode.PREECLAMPSIA,   None,                         "discordant", "2026-08-06T13:00:00"),
    (7,  2, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  DiagnosisCode.GESTATIONAL_HTN,None,                         "discordant", "2026-08-07T15:30:00"),
    (8,  1, DiagnosisCode.GESTATIONAL_HTN,  DiagnosisCode.PREECLAMPSIA,     CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  DiagnosisCode.GESTATIONAL_HTN,None,                         "discordant", "2026-08-08T11:20:00"),
    (9,  1, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  DiagnosisCode.CHRONIC_HTN,    DiagnosisCode.PREECLAMPSIA,   "three_way",  "2026-08-09T16:00:00"),
    (10, 2, DiagnosisCode.PREECLAMPSIA,     DiagnosisCode.GESTATIONAL_HTN,  CertaintyLevel.PROBABLE,  CertaintyLevel.PROBABLE,  DiagnosisCode.NOT_PE,         DiagnosisCode.PREECLAMPSIA,   "three_way",  "2026-08-10T12:00:00"),
]



def seed_e2e_packet(db) -> dict:
    """
    Seed the deterministic 12-subject E2E packet.

    Returns:
      {
        'users':       {email: PortalUser},
        'participants': [dict, ...],   # 10 valid participant summary dicts
        'assignments':  [SubjectAssignment, ...],
      }
    """
    users = seed_e2e_users(db)
    db.commit()

    participant_summaries = []

    adj_a_upn = "adj_a@test.acrn"
    adj_b_upn = "adj_b@test.acrn"

    for (n, visit_number, diag_a, diag_b, cert_a, cert_b, diag_c, final_chair_diag, path, dod_str) in _SUBJECT_TABLE:
        subj = _subject(n, visit_number)

        # Create participant if not exists
        p = db.query(Participant).filter_by(
            subject_id=subj["subject_id"], study=STUDY
        ).first()
        if not p:
            p = Participant(
                subject_id=subj["subject_id"],
                case_number=subj["case_number"],
                site_code="ZWE999",
                site_name="E2E Simulation Site",
                study=STUDY,
                status=AdjudicationStatus.PENDING,
                visit_count=visit_number,
                qc_approved=False,
            )
            db.add(p)
        else:
            p.visit_count = visit_number
            p.qc_approved = False
        db.flush()
        participant_summaries.append({
            "id": p.id,
            "subject_id": p.subject_id,
            "case_number": p.case_number,
            "visit_count": p.visit_count,
            "visit_number": visit_number,
            "site_code": p.site_code,
            "diag_a": diag_a,
            "diag_b": diag_b,
            "cert_a": cert_a,
            "cert_b": cert_b,
            "diag_c": diag_c,
            "final_chair_diag": final_chair_diag,
            "path": path,
            "dod_str": dod_str,
        })

    db.commit()


    # Return lookup
    return {
        "users": users,
        "participants": participant_summaries,
        "adj_a_upn": adj_a_upn,
        "adj_b_upn": adj_b_upn,
        "adj_c_upn": "adj_c@test.acrn",
        "chair_upn": "chair@test.acrn",
        "monitor_upn": "monitor@test.acrn",
        "subject_table": _SUBJECT_TABLE,
    }


# ── Malformed import CSV (for Stage 1 import rejection tests) ─────────────────

MALFORMED_EDC_CSV = """SUBJID,CaseNo,SiteCode,SiteName,TriggerCode,GA_EVENT,SBP,DBP,EVENT_DT
ZWE999-IMP-01,ADJ-IMP-01,ZWE999,E2E Site,DV-30,32+1,168,98,2026-08-01
ZWE999-IMP-02,ADJ-IMP-02,ZWE999,E2E Site,DV-30,31+4,174,102,2026-08-02
,MALFORMED-01,ZWE999,E2E Site,DV-30,33+0,160,95,2026-08-03
,MALFORMED-02,ZWE999,E2E Site,DV-30,35+2,158,92,2026-08-04
"""

BLINDING_VIOLATION_CSV = """SUBJID,CaseNo,SiteCode,SiteName,TriggerCode,SFLT1,PlGF_RATIO
ZWE999-BAD-01,ADJ-BAD-01,ZWE999,E2E Site,DV-30,2100,0.38
"""

