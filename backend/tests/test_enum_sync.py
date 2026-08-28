"""Guards for the enum reconciliation that init_prod runs before the migrations.

sync_enum_labels itself talks to pg_enum and needs a real Postgres, so what is pinned
here is the part that decides WHAT to reconcile -- the step that was missing when
REVIEWER_C shipped to production without ever reaching the reviewerrole type.
"""
from database import Base
from models.canonical import (  # noqa: F401  (import registers the tables)
    AdjudicationRecord, CommitteeDecision, DiagnosisCode, ReviewerRole,
)
from scripts.enum_sync import model_enum_columns


def _labels_for(table, column):
    for table_name, column_name, labels in model_enum_columns(Base.metadata):
        if (table_name, column_name) == (table, column):
            return labels
    raise AssertionError(f"{table}.{column} is not reported as a native enum column")


def test_reviewer_role_column_reports_every_role_including_reviewer_c_and_chair():
    labels = _labels_for("adjudication_records", "reviewer_role")
    assert labels == [role.name for role in ReviewerRole]
    # The two that production's reviewerrole type was missing.
    assert "REVIEWER_C" in labels
    assert "CHAIR" in labels


def test_diagnosis_labels_are_member_names_and_exclude_the_preeclampsia_alias():
    labels = _labels_for("adjudication_records", "diagnosis")
    # SQLAlchemy persists member names, not values ("Severe PE" is never written).
    assert "SEVERE_PE" in labels
    assert "Severe PE" not in labels
    # PREECLAMPSIA is an alias of PE, so it is not a distinct label and must not be
    # offered to ALTER TYPE ... ADD VALUE.
    assert "PREECLAMPSIA" not in labels
    assert DiagnosisCode.PREECLAMPSIA is DiagnosisCode.PE


def test_committee_decision_enum_columns_are_covered():
    reported = {
        (table, column) for table, column, _ in model_enum_columns(Base.metadata)
    }
    assert ("committee_decisions", "adopted_reviewer") in reported
    assert ("committee_decisions", "final_diagnosis") in reported


def test_every_reported_column_has_at_least_one_label():
    for table_name, column_name, labels in model_enum_columns(Base.metadata):
        assert labels, f"{table_name}.{column_name} reported with no labels"
