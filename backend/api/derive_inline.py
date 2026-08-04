"""
Inline Derivation API — POST /api/derive/inline
================================================
Accepts a case JSON payload (no subject ID / database required).
Returns the full DV-01 through DV-30 derivation result.

This endpoint enables the frontend to call the validated backend engine
directly during CSV upload and active case review, with graceful degradation
to the JS mirror engine when offline.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

from services.derivation_engine import (
    run_full_derivation,
    CriterionResult,
    RULE_VERSION,
)

router = APIRouter()


class BpReading(BaseModel):
    sbp: Optional[float] = None
    dbp: Optional[float] = None
    date: Optional[str] = None
    datetime: Optional[str] = None
    ga: Optional[str] = None
    source: Optional[str] = None
    severe: Optional[bool] = None


class LabEntry(BaseModel):
    analyte: Optional[str] = None
    result: Optional[str] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    severe: Optional[bool] = None


class ProtEntry(BaseModel):
    date: Optional[str] = None
    method: Optional[str] = None
    result: Optional[str] = None
    numeric: Optional[float] = None
    severe: Optional[bool] = None


class InlineCasePayload(BaseModel):
    """Flexible case data payload for inline derivation."""
    id: Optional[str] = None
    # Dating
    firstUssDate: Optional[str] = None
    firstUssGa: Optional[str] = None
    edd: Optional[str] = None
    lnmp: Optional[str] = None
    # BP
    bpLog: Optional[List[BpReading]] = []
    bp_readings: Optional[List[BpReading]] = []
    # Proteinuria
    upcr: Optional[float] = None
    dipstick_raw: Optional[Any] = None
    prot_24h_mg: Optional[float] = None
    proteinuriaLog: Optional[List[ProtEntry]] = []
    # Labs
    platelet_count: Optional[float] = None
    creatinine: Optional[float] = None
    creatinine_raw: Optional[Any] = None
    creatinine_unit: Optional[str] = None
    baseline_creatinine: Optional[float] = None
    ast: Optional[float] = None
    alt: Optional[float] = None
    ldh: Optional[float] = None
    labLog: Optional[List[LabEntry]] = []
    # Fetal
    efw_centile: Optional[float] = None
    efw_grams: Optional[float] = None
    ua_aedf: Optional[bool] = None
    ua_redf: Optional[bool] = None
    abruption: Optional[bool] = None
    iufd: Optional[bool] = None
    # Onset
    ga_at_first_criterion: Optional[str] = None
    gaAtEvent: Optional[str] = None
    # Clinical events
    seizure_documented: Optional[Any] = None
    mgso4_exposure: Optional[Any] = None
    dic_documented: Optional[bool] = None
    pulm_oedema_documented: Optional[bool] = None
    icu_admission: Optional[bool] = None
    maternal_death: Optional[bool] = None
    cerebral_event: Optional[bool] = None
    blood_transfusion: Optional[bool] = None
    hepatic_failure: Optional[bool] = None
    rds: Optional[bool] = None
    nec: Optional[bool] = None
    ivh: Optional[bool] = None
    neonatal_death: Optional[bool] = None
    # Delivery
    delivery_date: Optional[str] = None
    ga_at_delivery: Optional[str] = None
    gaAtDelivery: Optional[str] = None
    # Obstetric history
    gravidity: Optional[int] = None
    parity: Optional[int] = None
    # Weight / medications
    weightLog: Optional[List[Dict]] = []
    medicationLog: Optional[List[Dict]] = []
    # Source docs
    sourceDocs: Optional[Dict] = {}
    # Submissions for DV-29
    submissions: Optional[List[Dict]] = []


def _criterion_to_dict(r: CriterionResult) -> dict:
    """Serialise a CriterionResult dataclass to a JSON-safe dict."""
    d = {
        "id": r.criterion_id,
        "met": r.met,
        "formula": r.formula,
        "inputs": r.inputs or {},
        "source_fields": r.source_fields or [],
        "notes": r.notes,
        "rule_version": r.rule_version,
    }
    if r.first_date_met:
        d["first_date_met"] = r.first_date_met.isoformat() if isinstance(r.first_date_met, datetime) else str(r.first_date_met)
    if r.gestational_age_at_event:
        d["gestational_age_at_event"] = r.gestational_age_at_event
    if r.missingness_status:
        d["missingness_status"] = r.missingness_status
    return d


@router.post("/derive/inline")
def derive_inline(payload: InlineCasePayload):
    """
    Run the full ISSHP 2021 validated derivation engine against a case JSON payload.
    No database required — works purely from supplied data.
    Returns all DV results plus evidence score, certainty gate, and severity grade.
    """
    # Build the canonical case_data dict that run_full_derivation expects
    bp_list = [r.model_dump() for r in (payload.bpLog or payload.bp_readings or [])]
    lab_list = [r.model_dump() for r in (payload.labLog or [])]

    # Extract lab values from labLog if not top-level
    def find_lab(analyte_substr):
        for lab in lab_list:
            if lab.get("analyte") and analyte_substr.lower() in lab["analyte"].lower():
                try:
                    return float(lab["result"])
                except (ValueError, TypeError):
                    return None
        return None

    case_data = payload.model_dump()
    case_data["bp_readings"] = bp_list

    # Fill missing top-level values from labLog
    if case_data.get("platelet_count") is None:
        case_data["platelet_count"] = find_lab("platelet")
    if case_data.get("creatinine") is None:
        creat_str = next((l["result"] for l in lab_list if l.get("analyte") and "creatinine" in l["analyte"].lower()), None)
        creat_unit = next((l.get("unit") for l in lab_list if l.get("analyte") and "creatinine" in l["analyte"].lower()), None)
        case_data["creatinine_raw"] = creat_str
        case_data["creatinine_unit"] = creat_unit
    if case_data.get("ast") is None:
        case_data["ast"] = find_lab("ast")
    if case_data.get("alt") is None:
        case_data["alt"] = find_lab("alt")
    if case_data.get("ldh") is None:
        case_data["ldh"] = find_lab("ldh")

    # Use gaAtEvent as fallback for ga_at_first_criterion
    if not case_data.get("ga_at_first_criterion") and case_data.get("gaAtEvent"):
        case_data["ga_at_first_criterion"] = case_data["gaAtEvent"]

    # Run the full derivation engine
    results = run_full_derivation(case_data)

    # Serialise all CriterionResult objects
    serialised = {}
    for k, v in results.items():
        if isinstance(v, CriterionResult):
            serialised[k] = _criterion_to_dict(v)
        elif isinstance(v, list):
            serialised[k] = v
        elif isinstance(v, (str, float, int, bool, dict)) or v is None:
            serialised[k] = v
        else:
            serialised[k] = str(v)

    # Build backward-compatible criteria array
    criteria_results = []
    dv_criteria_map = {
        "HTN-01": ("HTN-01", "Hypertension (≥140/90 mmHg, confirmed)"),
        "HTN-02": ("HTN-02", "Severe-range BP (≥160/110 mmHg)"),
        "PROT-01": ("PROT-01", "Significant Proteinuria"),
        "HAEM-01": ("HAEM-01", "Thrombocytopenia"),
        "RENAL-01": ("RENAL-01", "Renal Impairment"),
        "HEP-01": ("HEP-01", "Hepatic Dysfunction"),
        "HEP-02": ("HEP-02", "LDH Elevation"),
        "COMP-01": ("HELLP-01", "HELLP Syndrome"),
        "SEV-01": ("SEV-01", "Severe Features"),
        "FGR-01": ("FGR-01", "Fetal Growth Restriction"),
        "DOPP-01": ("DOPP-01", "Abnormal Doppler"),
    }
    for engine_id, (ui_id, title) in dv_criteria_map.items():
        r = results.get(engine_id)
        if isinstance(r, CriterionResult):
            criteria_results.append({
                "id": ui_id, "title": title,
                "met": r.met, "details": r.notes or r.formula or ""
            })

    return {
        "status": "success",
        "subject_id": payload.id or "INLINE",
        "rule_version": RULE_VERSION,
        "evidence_completeness_score": results.get("evidence_completeness_score", 0),
        "missing_anchors": results.get("missing_anchors", []),
        "certainty_gate_passed": results.get("certainty_gate_passed", False),
        "criteria": criteria_results,
        "derivation_results": serialised,
    }
