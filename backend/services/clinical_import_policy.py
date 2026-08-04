"""Clinical ingestion boundary: source-recorded PE outcomes never become adjudication answers."""
import re
from fastapi import HTTPException

RECORDED_OUTCOME_PATTERNS = (
    "preeclampsia status", "pre-eclampsia status", "pe status", "pe_status",
    "preeclampsia diagnosis", "pre-eclampsia diagnosis", "pe diagnosis", "pe_diagnosis",
    "preeclampsia diagnosed", "pre-eclampsia diagnosed", "pe diagnosed",
    "recorded pe", "recorded_pe", "diagnosis date", "diagnosis_date",
    "pe outcome", "pe_outcome", "final diagnosis", "final_diagnosis",
)
OUTCOME_CANONICAL_FIELDS = {
    "RECORDED_PE_STATUS", "RECORDED_PE_DIAGNOSIS", "RECORDED_PE_DIAGNOSIS_DATE",
    "PE_STATUS", "PE_DIAGNOSIS", "FINAL_DIAGNOSIS", "ADJUDICATION_OUTCOME",
}

def normalized(value): return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def is_recorded_pe_outcome(*labels):
    text = " | ".join(normalized(x) for x in labels)
    return any(normalized(p) in text for p in RECORDED_OUTCOME_PATTERNS)

def classify_realtime_field(form_title="", page_title="", field_label="", export_variable_name=""):
    if is_recorded_pe_outcome(form_title, page_title, field_label, export_variable_name):
        return "RESTRICTED_RECORDED_OUTCOME"
    return "PERMITTED_OR_UNMAPPED"

def assert_not_adjudicator_outcome_mapping(source_field, canonical_field):
    if is_recorded_pe_outcome(source_field) or str(canonical_field or "").upper() in OUTCOME_CANONICAL_FIELDS:
        raise HTTPException(422, "Recorded PE status/diagnosis is restricted comparison metadata and cannot populate adjudicator-facing evidence or derivation inputs.")

def evidence_only_payload(row):
    """Remove recorded outcome keys before any derivation or adjudicator serialization."""
    return {k:v for k,v in row.items() if not is_recorded_pe_outcome(k) and str(k).upper() not in OUTCOME_CANONICAL_FIELDS}
