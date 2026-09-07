"""
ACRN PROTECT-Africa / LOPE-Nigeria Endpoint Adjudication Platform
Unified Demo Environment Reset & Reseed Service
"""

import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from database import DB_OFFLINE
from models.auth import PortalUser, AuthSession, AuthAuditEvent, CommitteeAssignment
from models.admin import (
    AdminUser, AdminRole, UserRole, StudyAccess, AdminStudy, AdminSite,
    ControlledVersion, IntegrationStatus, AccessReview, AdminAuditEvent,
    AdjudicationActivityLedger
)
from models.canonical import (
    Participant, AdjudicationVisit, AdjudicationRecord, CommitteeDecision,
    CommitteeMeeting, SignedCaseArtifact, VisitMeasurementDate, CanonicalField,
    DerivationResult, Narrative, AuditEvent, SubjectAssignment, ImportBatch,
    StudyCode, AdjudicationStatus, ReviewerRole, DiagnosisCode, OnsetClass,
    SeverityGrade, CertaintyLevel
)
from models.longitudinal import (
    RTImportBatch, LongitudinalParticipant, VisitInstance, CanonicalObservation,
    ReviewerAssignment, RestrictedIdentityCrosswalk, VisitDerivation,
    LongitudinalCaseDerivation, ImportIssue
)
from models.history import PatientHistory, PatientHistoryField, PatientRiskSummary
from models.monitor import MonitorRecord, MonitorImportBatch, ReconciliationItem

from services.auth_service import seed_demo_accounts, DEMO_ACCOUNTS
from services.admin_demo import seed_demo

logger = logging.getLogger("acrn.demo_reset")


def is_demo_environment() -> bool:
    """Check whether demo features/data are permitted in current environment."""
    return any(
        os.getenv(flag, "false").strip().lower() == "true"
        for flag in ("ENABLE_DEMO_DATA", "ENABLE_DEMO_ACCOUNTS")
    ) or DB_OFFLINE


def purge_all_demo_data(db: Session) -> dict[str, int]:
    """Safely purge all synthetic and demonstration records from all tables."""
    counts = {}

    def _delete(model, *filters):
        q = db.query(model)
        for f in filters:
            q = q.filter(f)
        count = q.delete(synchronize_session=False)
        counts[model.__tablename__] = count
        return count

    # 1. Clinical Adjudication & Artifacts
    _delete(SignedCaseArtifact)
    _delete(VisitMeasurementDate)
    _delete(CommitteeDecision)
    _delete(AdjudicationRecord)
    _delete(CommitteeMeeting)
    _delete(SubjectAssignment)
    _delete(Narrative)
    _delete(DerivationResult)
    _delete(CanonicalField)
    _delete(AuditEvent)
    _delete(AdjudicationVisit)
    _delete(Participant)
    _delete(ImportBatch)

    # 2. Longitudinal & RealTime Tables
    _delete(PatientHistoryField)
    _delete(PatientHistory)
    _delete(PatientRiskSummary)
    _delete(VisitDerivation)
    _delete(ImportIssue)
    _delete(CanonicalObservation)
    _delete(ReviewerAssignment)
    _delete(LongitudinalCaseDerivation)
    _delete(RestrictedIdentityCrosswalk)
    _delete(VisitInstance)
    _delete(LongitudinalParticipant)
    _delete(RTImportBatch)

    # 3. Monitor Tables
    _delete(MonitorRecord)
    _delete(MonitorImportBatch)
    _delete(ReconciliationItem)

    # 4. Admin Governance & Ledger
    _delete(AdjudicationActivityLedger)
    _delete(AdminAuditEvent)
    _delete(AccessReview)
    _delete(IntegrationStatus)
    _delete(ControlledVersion)
    _delete(AdminSite)
    _delete(StudyAccess)
    _delete(UserRole)
    _delete(AdminRole)
    _delete(AdminStudy)
    _delete(AdminUser)

    # 5. Clear Stale Auth Sessions
    _delete(AuthSession)

    db.commit()
    return counts

def purge_csv_scenarios(db: Session) -> dict[str, int]:
    """Scoped reset: deletes CSV/demo batches and their participants/assignments, preserving non-CSV batches."""
    from sqlalchemy import or_
    counts = {}
    csv_batches = db.query(ImportBatch).filter(
        or_(
            ImportBatch.edc_filename.ilike("%.csv"),
            ImportBatch.esource_filename.ilike("%.csv"),
            ImportBatch.edc_filename.ilike("%demo%"),
            ImportBatch.esource_filename.ilike("%demo%"),
        )
    ).all()
    csv_batch_ids = [b.id for b in csv_batches]
    participant_ids = [
        p.id for p in db.query(Participant.id)
        .filter(Participant.import_batch_id.in_(csv_batch_ids))
        .all()
    ] if csv_batch_ids else []
    visit_ids = [
        v.id for v in db.query(AdjudicationVisit.id)
        .filter(AdjudicationVisit.participant_id.in_(participant_ids))
        .all()
    ] if participant_ids else []

    rt_batches = db.query(RTImportBatch).filter(
        or_(RTImportBatch.filename.ilike("%.csv"), RTImportBatch.filename.ilike("%demo%"))
    ).all()
    rt_batch_ids = [b.id for b in rt_batches]
    rt_participant_ids = [
        p.id for p in db.query(LongitudinalParticipant.id)
        .filter(LongitudinalParticipant.source_batch_id.in_(rt_batch_ids))
        .all()
    ] if rt_batch_ids else []
    rt_visit_ids = [
        v.id for v in db.query(VisitInstance.id)
        .filter(VisitInstance.source_batch_id.in_(rt_batch_ids))
        .all()
    ] if rt_batch_ids else []

    def delete_count(model, *criteria):
        q = db.query(model)
        for criterion in criteria:
            q = q.filter(criterion)
        count = q.delete(synchronize_session=False)
        counts[model.__tablename__] = counts.get(model.__tablename__, 0) + count

    if visit_ids:
        delete_count(SignedCaseArtifact, SignedCaseArtifact.visit_id.in_(visit_ids))
        delete_count(VisitMeasurementDate, VisitMeasurementDate.visit_id.in_(visit_ids))
        delete_count(CommitteeDecision, CommitteeDecision.visit_id.in_(visit_ids))
        delete_count(AdjudicationRecord, AdjudicationRecord.visit_id.in_(visit_ids))
    if participant_ids:
        delete_count(SubjectAssignment, SubjectAssignment.participant_id.in_(participant_ids))
        delete_count(Narrative, Narrative.participant_id.in_(participant_ids))
        delete_count(DerivationResult, DerivationResult.participant_id.in_(participant_ids))
        delete_count(CanonicalField, CanonicalField.participant_id.in_(participant_ids))
        delete_count(AuditEvent, AuditEvent.participant_id.in_(participant_ids))
    if visit_ids:
        delete_count(AdjudicationVisit, AdjudicationVisit.id.in_(visit_ids))
    if participant_ids:
        delete_count(Participant, Participant.id.in_(participant_ids))
    if csv_batch_ids:
        delete_count(AuditEvent, AuditEvent.import_batch_id.in_(csv_batch_ids))
        delete_count(ImportBatch, ImportBatch.id.in_(csv_batch_ids))

    if rt_visit_ids:
        delete_count(VisitDerivation, VisitDerivation.visit_id.in_(rt_visit_ids))
        delete_count(ImportIssue, ImportIssue.visit_id.in_(rt_visit_ids))
        delete_count(CanonicalObservation, CanonicalObservation.visit_id.in_(rt_visit_ids))
    if rt_participant_ids:
        delete_count(ReviewerAssignment, ReviewerAssignment.participant_id.in_(rt_participant_ids))
        delete_count(LongitudinalCaseDerivation, LongitudinalCaseDerivation.participant_id.in_(rt_participant_ids))
        delete_count(RestrictedIdentityCrosswalk, RestrictedIdentityCrosswalk.participant_id.in_(rt_participant_ids))
        delete_count(ImportIssue, ImportIssue.participant_id.in_(rt_participant_ids))
        delete_count(PatientHistoryField, PatientHistoryField.participant_id.in_(rt_participant_ids))
        delete_count(PatientHistory, PatientHistory.participant_id.in_(rt_participant_ids))
        delete_count(PatientRiskSummary, PatientRiskSummary.participant_id.in_(rt_participant_ids))
    if rt_visit_ids:
        delete_count(VisitInstance, VisitInstance.id.in_(rt_visit_ids))
    if rt_participant_ids:
        delete_count(LongitudinalParticipant, LongitudinalParticipant.id.in_(rt_participant_ids))
    if rt_batch_ids:
        delete_count(ImportIssue, ImportIssue.batch_id.in_(rt_batch_ids))
        delete_count(RTImportBatch, RTImportBatch.id.in_(rt_batch_ids))

    db.commit()
    return counts


def seed_baseline_cases(db: Session) -> dict[str, int]:
    """
    Seeds a deterministic, ready-to-test baseline distribution of 12 participant cases
    with complete visit-level data and clinical evidence:
      - 4 Concordant cases (Reviewer A = Reviewer B)
      - 3 Discordant cases (Reviewer A != Reviewer B, ready for Reviewer C / Arbitrator)
      - 2 Three-Way Divergent cases (Reviewer A != B != C, ready for Committee Minutes)
      - 3 Fresh in-review cases (assigned to Reviewer A and B for testing)
    """
    now = datetime.utcnow()
    batch = ImportBatch(
        study=StudyCode.EOPE,
        edc_filename="protect_africa_baseline_demo.csv",
        esource_filename="protect_africa_baseline_esource_demo.csv",
        edc_export_date=now - timedelta(days=5),
        esource_export_date=now - timedelta(days=5),
        edc_row_count=240,
        esource_row_count=180,
        mapping_version="MAP-PROTECT-2.1",
        imported_by="system.demo.seed@acrnhealth.com",
        status="COMPLETE",
    )
    db.add(batch)
    db.flush()

    # Known distribution configuration:
    # (subject_num, visit_count, diag_a, diag_b, cert_a, cert_b, diag_c, status, onset, severity, criteria_a, criteria_b)
    CASE_CONFIGS = [
        # 1-4: Concordant cases
        (1, 2, DiagnosisCode.PE, DiagnosisCode.PE, CertaintyLevel.DEFINITE, CertaintyLevel.DEFINITE, None, AdjudicationStatus.CONCORDANT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, True),
        (2, 1, DiagnosisCode.PE, DiagnosisCode.PE, CertaintyLevel.DEFINITE, CertaintyLevel.DEFINITE, None, AdjudicationStatus.CONCORDANT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, True),
        (3, 3, DiagnosisCode.OTHER, DiagnosisCode.OTHER, CertaintyLevel.PROBABLE, CertaintyLevel.PROBABLE, None, AdjudicationStatus.CONCORDANT, OnsetClass.LOPE, SeverityGrade.WITHOUT_SEVERE, False, False),
        (4, 1, DiagnosisCode.PE, DiagnosisCode.PE, CertaintyLevel.DEFINITE, CertaintyLevel.DEFINITE, None, AdjudicationStatus.CONCORDANT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, True),
        # 5-7: Discordant cases (Reviewer A != Reviewer B, Reviewer C active/pending)
        (5, 2, DiagnosisCode.PE, DiagnosisCode.OTHER, CertaintyLevel.DEFINITE, CertaintyLevel.PROBABLE, DiagnosisCode.PE, AdjudicationStatus.DISCORDANT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, False),
        (6, 1, DiagnosisCode.PE, DiagnosisCode.NOT_PE, CertaintyLevel.PROBABLE, CertaintyLevel.NOT_PE, None, AdjudicationStatus.DISCORDANT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, False),
        (7, 2, DiagnosisCode.OTHER, DiagnosisCode.PE, CertaintyLevel.POSSIBLE, CertaintyLevel.DEFINITE, DiagnosisCode.OTHER, AdjudicationStatus.DISCORDANT, OnsetClass.LOPE, SeverityGrade.WITH_SEVERE, False, True),
        # 8-9: Three-way divergent cases (A != B != C)
        (8, 1, DiagnosisCode.PE, DiagnosisCode.OTHER, CertaintyLevel.PROBABLE, CertaintyLevel.PROBABLE, DiagnosisCode.NOT_PE, AdjudicationStatus.THREE_WAY_DIVERGENT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, False),
        (9, 2, DiagnosisCode.PE, DiagnosisCode.NOT_PE, CertaintyLevel.DEFINITE, CertaintyLevel.NOT_PE, DiagnosisCode.OTHER, AdjudicationStatus.THREE_WAY_DIVERGENT, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, False),
        # 10-12: Fresh in-review cases (assigned to Reviewer A & B, pending review)
        (10, 1, None, None, None, None, None, AdjudicationStatus.IN_REVIEW, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, True),
        (11, 2, DiagnosisCode.PE, None, CertaintyLevel.DEFINITE, None, None, AdjudicationStatus.IN_REVIEW, OnsetClass.EOPE, SeverityGrade.WITH_SEVERE, True, True),
        (12, 1, None, None, None, None, None, AdjudicationStatus.PENDING, OnsetClass.LOPE, SeverityGrade.WITHOUT_SEVERE, False, False),
    ]

    adj_a_upn = "adjudicatora@acrnhealth.com"
    adj_b_upn = "adjudicatorb@acrnhealth.com"
    adj_c_upn = "adjudicatorc@acrnhealth.com"

    sample_rationale_template = (
        "SECTION 1 — CASE METADATA AND IDENTIFIER\n"
        "Participant ID: {sid}\n"
        "Form: FORM-ADJ-15A (Blinded Clinical Narrative)\n"
        "Site / Provider: [Blinded per SOP-ADJ-002]\n"
        "Protocol Scope: PROTECT-Africa / LOPE-Nigeria\n\n"
        "SECTION 2 — ENDPOINT / PREDICTION WINDOW\n"
        "Estimated Delivery Date (EDD): 14/Oct/2026\n"
        "Gestational Age at Event Presentation: 31+4\n"
        "Triggering Event: DV-30 (Severe BP Recheck)\n\n"
        "SECTION 3 — PREGNANCY DATING\n"
        "Dating Anchor: 1st-Trimester Ultrasound Anchor\n"
        "First USS Date: 02/Feb/2026\n"
        "GA at First USS: 11+2\n"
        "LMP Date: 12/Nov/2025\n\n"
        "SECTION 4 — CLINICAL PRESENTATION SUMMARY\n"
        "GA at Presentation: 31+4\n"
        "Gravidity: 2 | Parity: 1\n"
        "Derived Phenotype Subtype: EOPE\n"
        "Derived Severity: With severe features\n\n"
        "SECTION 5 — BLOOD PRESSURE COURSE\n"
        "Serial BP Readings: 164/112 mmHg (GA 31+4); 168/110 mmHg (GA 31+4)\n"
        "Peak BP Measurement: 168/112 mmHg\n"
        "Severe Range BP (≥160/110): Yes (≥160/110 mmHg severe-range criterion met)\n\n"
        "SECTION 6 — PROTEINURIA EVIDENCE\n"
        "UPCR Quantitation: 0.48 g/g\n"
        "Dipstick Result: 3+\n"
        "Assessment Summary: UPCR quantitation ≥0.3 confirmed\n\n"
        "SECTION 7 — LABORATORY COURSE (HAEMATOLOGY AND BIOCHEMISTRY)\n"
        "Platelet Count: 88 ×10³/µL\n"
        "Creatinine: 96 umol/L\n"
        "Transaminases: AST 74 U/L | ALT 68 U/L\n"
        "LDH: 620 IU/L\n"
        "[Biomarker data (sFlt-1/PlGF/sEng/POC) strictly withheld per SOP-ADJ-002.]\n\n"
        "SECTION 8 — MATERNAL CLINICAL COURSE\n"
        "Medication Log: Labetalol (200mg BD), Magnesium Sulfate (4g IV loading)\n"
        "Weight Log: 68kg at GA 12+0 → 77kg at GA 31+4\n\n"
        "SECTION 9 — FETAL ASSESSMENT (GROWTH AND DOPPLER)\n"
        "Ultrasound & Doppler Findings: EFW 1340g (8th centile), Umbilical artery PI elevated\n"
        "EFW Centile: 8th centile\n"
        "Umbilical Artery AEDF: Yes (AEDF documented)\n\n"
        "SECTION 10 — DELIVERY RECORD\n"
        "Delivery Date: 28/Mar/2026\n"
        "GA at Delivery: 32+1\n"
        "Delivery Record: Emergency Caesarean section indicated for maternal severe preeclampsia and fetal compromise.\n\n"
        "SECTION 11 — MATERNAL OUTCOME\n"
        "Maternal SAEs / Complications: Severe pre-eclampsia with thrombocytopenia. Resolved post-delivery.\n\n"
        "SECTION 12 — NEONATAL OUTCOME\n"
        "Neonatal Outcome: Liveborn neonate, birthweight 1380g, APGAR 7/9. Admitted to NICU for prematurity.\n\n"
        "SECTION 13 — MISSING DATA, DISCREPANCIES AND OUTSTANDING QUERIES\n"
        "Evidence Completeness Score: 100%\n"
        "Reviewer notes: Contemporaneous clinical evidence confirms early-onset preeclampsia with severe features (severe hypertension, thrombocytopenia nadir 88, fetal growth restriction)."
    )

    participant_count = 0
    visit_count = 0
    record_count = 0

    # RealTime Batch
    rt_batch = RTImportBatch(
        filename="realtime_longitudinal_demo_snapshot.csv",
        checksum="demo-rt-baseline-checksum",
        file_size=64200,
        uploaded_by="monitor1@acrnhealth.com",
        status="MONITOR_QC_REQUIRED",
        row_count=180,
        participant_count=len(CASE_CONFIGS),
        visit_count=18,
        validation_result="Passed",
        blinding_result="Passed",
    )
    db.add(rt_batch)
    db.flush()

    for cfg in CASE_CONFIGS:
        (n, v_cnt, diag_a, diag_b, cert_a, cert_b, diag_c, status, onset, severity, crit_a, crit_b) = cfg
        sid = f"ACRN-DEMO-{n:04d}"
        case_no = f"ADJ-{n:04d}"
        site = "ZWE001" if n % 2 == 1 else "NGA004"
        study = StudyCode.EOPE if onset == OnsetClass.EOPE else StudyCode.LOPE

        # 1. Canonical Participant
        p = Participant(
            subject_id=sid,
            case_number=case_no,
            site_code=site,
            site_name="Harare Central Hospital" if site == "ZWE001" else "Lagos University Hospital",
            study=study,
            import_batch_id=batch.id,
            status=status,
            visit_count=v_cnt,
            qc_approved=True,
            trigger_code="DV-30",
        )
        db.add(p)
        db.flush()
        participant_count += 1

        # 2. Longitudinal Participant for RealTime
        lp = LongitudinalParticipant(
            blinded_subject_id=sid,
            study="PROTECT-Africa" if onset == OnsetClass.EOPE else "LOPE-Nigeria",
            site_code=site,
            participant_status="IMPORTED",
            available_visit_count=v_cnt,
            workflow_status="QC_RELEASED" if status == AdjudicationStatus.CONCORDANT else "MONITOR_QC_REQUIRED",
            maximum_severity=severity.value if hasattr(severity, "value") else str(severity),
            packet_completeness=1.0 if n <= 4 else 0.85,
            history_completeness=0.92,
            source_batch_id=rt_batch.id,
        )
        db.add(lp)
        db.flush()

        # Restricted Identity Crosswalk
        db.add(RestrictedIdentityCrosswalk(
            participant_id=lp.id,
            protected_mrn=f"MRN-{7000 + n}",
            screening_number=sid,
            source_system="RealTime",
        ))

        # Add Subject Assignments
        db.add(SubjectAssignment(
            participant_id=p.id,
            reviewer_a_upn=adj_a_upn,
            reviewer_b_upn=adj_b_upn,
            reviewer_c_upn=adj_c_upn if diag_c else None,
            assigned_at=now - timedelta(days=10),
            assigned_by="monitor1@acrnhealth.com",
            status="ASSIGNED",
        ))

        # Create Visits
        for v_num in range(1, v_cnt + 1):
            v_code = f"V{v_num:02d}"
            v_date = now - timedelta(days=30 - (v_num * 7))

            # Canonical Visit
            visit = AdjudicationVisit(
                participant_id=p.id,
                visit_number=v_num,
                visit_code=v_code,
                visit_date=v_date,
                status="COMPLETED" if (diag_a and diag_b) else "IN_REVIEW",
                resolution_type="CONCORDANT" if status == AdjudicationStatus.CONCORDANT else None,
            )
            db.add(visit)
            db.flush()
            visit_count += 1

            # RealTime Visit Instance
            db.add(VisitInstance(
                participant_id=lp.id,
                source_batch_id=rt_batch.id,
                scheduled_visit_code=f"Visit {v_num:02d}",
                form_title=f"Visit {v_num:02d}",
                visit_occurrence=1,
                visit_type="SCHEDULED",
                reconstruction_method="DEMO_SEED",
                reconstruction_confidence="HIGH",
                qc_status="PROCESSED",
            ))

            # Seed Reviewer A record if applicable
            if diag_a:
                rec_a = AdjudicationRecord(
                    participant_id=p.id,
                    visit_id=visit.id,
                    visit_number=v_num,
                    reviewer_upn=adj_a_upn,
                    reviewer_name="ACRN Demo Adjudicator A",
                    reviewer_role=ReviewerRole.REVIEWER_A,
                    diagnosis=diag_a,
                    certainty=cert_a or CertaintyLevel.DEFINITE,
                    meets_criteria=crit_a,
                    onset_class=onset,
                    severity=severity,
                    date_of_diagnosis=v_date,
                    differential_diagnosis="Gestational Hypertension" if diag_a != DiagnosisCode.PE else None,
                    rationale=sample_rationale_template.format(sid=sid),
                    comment="Reviewer A independent determination signed.",
                    signed=True,
                    signed_at=now - timedelta(days=3),
                )
                db.add(rec_a)
                record_count += 1

            # Seed Reviewer B record if applicable
            if diag_b:
                rec_b = AdjudicationRecord(
                    participant_id=p.id,
                    visit_id=visit.id,
                    visit_number=v_num,
                    reviewer_upn=adj_b_upn,
                    reviewer_name="ACRN Demo Adjudicator B",
                    reviewer_role=ReviewerRole.REVIEWER_B,
                    diagnosis=diag_b,
                    certainty=cert_b or CertaintyLevel.PROBABLE,
                    meets_criteria=crit_b,
                    onset_class=onset,
                    severity=severity,
                    date_of_diagnosis=v_date,
                    differential_diagnosis="Chronic HTN with Superimposed PE" if diag_b != DiagnosisCode.PE else None,
                    rationale=sample_rationale_template.format(sid=sid),
                    comment="Reviewer B independent determination signed.",
                    signed=True,
                    signed_at=now - timedelta(days=2),
                )
                db.add(rec_b)
                record_count += 1

            # Seed Reviewer C record if applicable
            if diag_c:
                rec_c = AdjudicationRecord(
                    participant_id=p.id,
                    visit_id=visit.id,
                    visit_number=v_num,
                    reviewer_upn=adj_c_upn,
                    reviewer_name="ACRN Demo Adjudicator C",
                    reviewer_role=ReviewerRole.REVIEWER_C,
                    diagnosis=diag_c,
                    certainty=CertaintyLevel.DEFINITE,
                    meets_criteria=True,
                    onset_class=onset,
                    severity=severity,
                    date_of_diagnosis=v_date,
                    rationale=sample_rationale_template.format(sid=sid),
                    comment="Reviewer C arbitration review completed.",
                    signed=True,
                    signed_at=now - timedelta(days=1),
                )
                db.add(rec_c)
                record_count += 1

            # Seed Committee Decision for Concordant/Resolved cases on primary visit
            if status == AdjudicationStatus.CONCORDANT and v_num == 1:
                db.add(CommitteeDecision(
                    participant_id=p.id,
                    visit_id=visit.id,
                    visit_number=1,
                    final_diagnosis=diag_a,
                    adopted_reviewer=ReviewerRole.REVIEWER_A,
                    chair_upn="chairperson@acrnhealth.com",
                    chair_name="ACRN Committee Chair",
                    chair_rationale="Concordant determination verified and locked per charter.",
                    date_of_diagnosis=v_date,
                    locked=True,
                    closed=True,
                    closed_at=now - timedelta(hours=12),
                    concordance_status="CONCORDANT_A_EQUALS_B",
                ))

    db.commit()
    return {
        "participants": participant_count,
        "visits": visit_count,
        "records": record_count,
    }


def reset_demo_environment(db: Session, reseed_cases: bool = True) -> dict:
    """
    Master reset function:
    1. Purges all synthetic and test data across all tables.
    2. Re-seeds demo accounts with default credentials (ACRN@2026).
    3. Re-seeds Admin governance fixtures (rules DV-01..30, studies, sites, mappings).
    4. Re-seeds Monitor records & batches.
    5. Re-seeds 12 structured demonstration cases across all workflow stages.
    """
    if not is_demo_environment():
        raise HTTPException(
            status_code=409,
            detail="Demo data reset is disabled in production environments. Set ENABLE_DEMO_ACCOUNTS=true or ENABLE_DEMO_DATA=true."
        )

    # 1. Purge everything cleanly
    purged_counts = purge_all_demo_data(db)

    # 2. Re-seed accounts
    accounts_seeded = seed_demo_accounts(db, force_password_reset=True)

    # 3. Re-seed Admin fixtures
    seed_demo(db)

    # 4. Re-seed Monitor fixtures
    from api.monitor import seed as seed_monitor
    seed_monitor(db)

    # 5. Re-seed baseline clinical cases
    cases_seeded = {}
    if reseed_cases:
        cases_seeded = seed_baseline_cases(db)

    return {
        "status": "SUCCESS",
        "timestamp": datetime.utcnow().isoformat(),
        "purged_records": purged_counts,
        "total_purged": sum(purged_counts.values()),
        "accounts_active": len(DEMO_ACCOUNTS),
        "accounts_reseeded": accounts_seeded,
        "cases_reseeded": cases_seeded,
    }
