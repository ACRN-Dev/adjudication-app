"""
Unit and Integration Tests for Visit 5 Fetal and Neonatal Adjudication Workflow
Remapped closed-ended assessments, mutual exclusivity, provenance, concordance, PDF, and export.
"""

import uuid
from datetime import datetime
from pathlib import Path
import pytest

from services.visit5_service import (
    map_source_to_visit5_assessments,
    validate_visit5_submission,
    compare_visit5_concordance,
    extract_visit5_source_evidence,
    ASSESSMENT_CODES,
)
from conftest import TestingSession
from models.canonical import (
    AdjudicationRecord,
    AdjudicationVisit,
    DiagnosisCode,
    Participant,
    ReviewerRole,
    SignedCaseArtifact,
    StudyCode,
    AdjudicationStatus,
    CanonicalField,
)
from services.case_finalization import finalize_case_pdf


class TestVisit5MappingAndEvidence:
    def test_term_normal_delivery_mapping(self):
        observations = [
            {
                "source_form": "Delivery Outcome",
                "source_field": "Gestational age at delivery",
                "raw_source_value": "39.2",
                "canonical_variable": "GA_AT_DELIVERY",
            },
            {
                "source_form": "Delivery Outcome",
                "source_field": "Outcome of pregnancy",
                "raw_source_value": "Normal baby",
                "canonical_variable": "PREGNANCY_OUTCOME",
            },
            {
                "source_form": "IUGR and SGA",
                "source_field": "Was IUGR confirmed?",
                "raw_source_value": "No",
                "canonical_variable": "CONFIRMED_IUGR",
            },
            {
                "source_form": "IUGR and SGA",
                "source_field": "Was SGA confirmed?",
                "raw_source_value": "No",
                "canonical_variable": "CONFIRMED_SGA",
            },
            {
                "source_form": "Newborn Assessment Form",
                "source_field": "Any birth complications?",
                "raw_source_value": "No",
                "canonical_variable": "BIRTH_COMPLICATIONS",
            },
        ]
        result = map_source_to_visit5_assessments(observations)
        assert result["gestational_age_at_delivery"] == 39.2
        assert result["pregnancy_outcome"] == "Normal baby"

        # Check assessments
        assessments = result["assessments"]
        assert assessments["DELIVERY_GE_37W"]["state"] == "CONFIRMED_POSITIVE"
        assert assessments["DELIVERY_LT_34W"]["state"] == "CONFIRMED_NEGATIVE"
        assert assessments["IUGR"]["state"] == "CONFIRMED_NEGATIVE"
        assert assessments["SGA"]["state"] == "CONFIRMED_NEGATIVE"
        assert assessments["PERINATAL_FETAL_DEATH"]["state"] == "CONFIRMED_NEGATIVE"
        assert assessments["NORMAL_OUTCOME"]["state"] == "CONFIRMED_POSITIVE"
        assert "DELIVERY_GE_37W" in result["suggested_assessments"]
        assert "NORMAL_OUTCOME" in result["suggested_assessments"]

    def test_preterm_with_iugr_and_sga_mapping(self):
        observations = [
            {
                "source_form": "Delivery Outcome",
                "source_field": "Gestational age at delivery",
                "raw_source_value": "31.5 weeks",
                "canonical_variable": "GA_AT_DELIVERY",
            },
            {
                "source_form": "Delivery Outcome",
                "source_field": "Outcome of pregnancy",
                "raw_source_value": "Preterm birth",
                "canonical_variable": "PREGNANCY_OUTCOME",
            },
            {
                "source_form": "IUGR and SGA",
                "source_field": "Was IUGR confirmed?",
                "raw_source_value": "Yes",
                "canonical_variable": "CONFIRMED_IUGR",
            },
            {
                "source_form": "IUGR and SGA",
                "source_field": "Was SGA confirmed?",
                "raw_source_value": "Yes",
                "canonical_variable": "CONFIRMED_SGA",
            },
        ]
        result = map_source_to_visit5_assessments(observations)
        assert result["gestational_age_at_delivery"] == 31.5
        assert result["pregnancy_outcome"] == "Preterm birth"

        assessments = result["assessments"]
        assert assessments["DELIVERY_LT_34W"]["state"] == "CONFIRMED_POSITIVE"
        assert assessments["DELIVERY_GE_37W"]["state"] == "CONFIRMED_NEGATIVE"
        assert assessments["IUGR"]["state"] == "CONFIRMED_POSITIVE"
        assert assessments["SGA"]["state"] == "CONFIRMED_POSITIVE"
        # Since adverse outcomes are positive, Normal outcome MUST be confirmed negative
        assert assessments["NORMAL_OUTCOME"]["state"] == "CONFIRMED_NEGATIVE"
        assert "NORMAL_OUTCOME" not in result["suggested_assessments"]
        assert "DELIVERY_LT_34W" in result["suggested_assessments"]
        assert "IUGR" in result["suggested_assessments"]
        assert "SGA" in result["suggested_assessments"]

    def test_missing_data_distinguished_from_negative(self):
        observations = [
            {
                "source_form": "Delivery Outcome",
                "source_field": "Gestational age at delivery",
                "raw_source_value": "38.0",
                "canonical_variable": "GA_AT_DELIVERY",
            },
            # IUGR and SGA form was never completed (missing)
        ]
        result = map_source_to_visit5_assessments(observations)
        assessments = result["assessments"]
        assert assessments["IUGR"]["state"] == "NOT_ASSESSED_OR_MISSING"
        assert assessments["SGA"]["state"] == "NOT_ASSESSED_OR_MISSING"
        assert assessments["IUGR"]["is_suggested"] is False


class TestVisit5ValidationRules:
    def test_normal_outcome_cannot_coexist_with_adverse(self):
        # NORMAL_OUTCOME with PERINATAL_FETAL_DEATH
        valid, msg = validate_visit5_submission(["NORMAL_OUTCOME", "PERINATAL_FETAL_DEATH"])
        assert valid is False
        assert "cannot coexist with adverse outcome" in msg

        # NORMAL_OUTCOME with IUGR
        valid, msg = validate_visit5_submission(["NORMAL_OUTCOME", "IUGR"])
        assert valid is False
        assert "cannot coexist with adverse outcome" in msg

        # NORMAL_OUTCOME with DELIVERY_LT_34W
        valid, msg = validate_visit5_submission(["NORMAL_OUTCOME", "DELIVERY_LT_34W"])
        assert valid is False

        # NORMAL_OUTCOME with SGA
        valid, msg = validate_visit5_submission(["NORMAL_OUTCOME", "SGA"])
        assert valid is False

    def test_delivery_ge_37w_and_lt_34w_mutually_exclusive(self):
        valid, msg = validate_visit5_submission(["DELIVERY_GE_37W", "DELIVERY_LT_34W"])
        assert valid is False
        assert "mutually exclusive" in msg

    def test_numeric_ga_consistency(self):
        # GA = 32 with DELIVERY_GE_37W
        valid, msg = validate_visit5_submission(["DELIVERY_GE_37W"], ga_at_delivery=32.0)
        assert valid is False
        assert "contradicts" in msg

        # GA = 38 with DELIVERY_LT_34W
        valid, msg = validate_visit5_submission(["DELIVERY_LT_34W"], ga_at_delivery=38.0)
        assert valid is False
        assert "contradicts" in msg

        # GA = 38 with DELIVERY_GE_37W is valid
        valid, msg = validate_visit5_submission(["DELIVERY_GE_37W", "NORMAL_OUTCOME"], ga_at_delivery=38.0)
        assert valid is True
        assert msg is None

    def test_perinatal_death_cannot_be_normal_baby(self):
        valid, msg = validate_visit5_submission(
            ["PERINATAL_FETAL_DEATH"],
            ga_at_delivery=30.0,
            pregnancy_outcome="Normal baby",
        )
        assert valid is False
        assert "Normal baby" in msg

    def test_valid_multiple_adverse_selections(self):
        valid, msg = validate_visit5_submission(
            ["DELIVERY_LT_34W", "IUGR", "SGA"],
            ga_at_delivery=31.2,
            pregnancy_outcome="Preterm birth",
        )
        assert valid is True
        assert msg is None


class TestVisit5Concordance:
    def test_exact_agreement(self):
        a = ["DELIVERY_LT_34W", "IUGR"]
        b = ["IUGR", "DELIVERY_LT_34W"]
        assert compare_visit5_concordance(a, b, 31.0, 31.2) is True

    def test_divergent_assessments(self):
        a = ["DELIVERY_LT_34W", "IUGR"]
        b = ["DELIVERY_LT_34W"]
        assert compare_visit5_concordance(a, b, 31.0, 31.0) is False

    def test_divergent_gestational_age(self):
        a = ["DELIVERY_GE_37W", "NORMAL_OUTCOME"]
        b = ["DELIVERY_GE_37W", "NORMAL_OUTCOME"]
        # GA discrepancy > 0.5 weeks
        assert compare_visit5_concordance(a, b, 37.0, 38.5) is False


class TestVisit5DatabaseAndPDFIntegration:
    def test_visit5_pdf_finalization_with_fetal_assessments(self, monkeypatch):
        monkeypatch.setenv("ETMF_ADAPTER", "local")
        output_root = Path(__file__).parent.parent / ".etmf_local" / "test-visit5-pdf"
        monkeypatch.setenv("ETMF_LOCAL_ROOT", str(output_root))

        db = TestingSession()
        try:
            suffix = uuid.uuid4().hex[:8]
            participant = Participant(
                subject_id=f"SUB-V5-{suffix}",
                case_number=f"CASE-V5-{suffix}",
                study=StudyCode.EOPE,
            )
            db.add(participant)
            db.flush()

            visit5 = AdjudicationVisit(
                participant_id=participant.id,
                visit_number=5,
                visit_code="V05",
                visit_date=datetime(2026, 9, 1),
                final_fetal_assessments=["DELIVERY_LT_34W", "IUGR", "SGA"],
            )
            db.add(visit5)
            db.flush()

            rec = AdjudicationRecord(
                participant_id=participant.id,
                visit_id=visit5.id,
                visit_number=5,
                reviewer_role=ReviewerRole.REVIEWER_A,
                reviewer_upn="rev_a@example.test",
                reviewer_name="Reviewer A",
                diagnosis=DiagnosisCode.SEVERE_PE,
                comment="Preterm delivery with documented fetal growth restriction.",
                signed=True,
                signed_at=datetime(2026, 9, 2, 10),
                signature_hash="b" * 64,
                fetal_neonatal_assessments=["DELIVERY_LT_34W", "IUGR", "SGA"],
                gestational_age_at_delivery=31.4,
                pregnancy_outcome="Preterm birth",
                fetal_assessment_status="CONFIRMED",
            )
            db.add(rec)
            db.flush()

            pdf_artifact = finalize_case_pdf(db, participant, visit5, rec)
            db.commit()

            assert pdf_artifact is not None
            assert Path(pdf_artifact.storage_reference).exists()
            assert Path(pdf_artifact.storage_reference).read_bytes().startswith(b"%PDF")
        finally:
            db.close()
