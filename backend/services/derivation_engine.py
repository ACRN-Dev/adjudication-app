"""
ACRN PROTECT-Africa Clinical Derivation Engine
================================================
Deterministic ISSHP 2021 / ACOG preeclampsia diagnostic criteria.

CRITICAL DESIGN PRINCIPLE (Dr. Makadzange):
  "The AI should not decide whether numeric diagnostic thresholds are met.
   That should be conventional validated code."

Enhanced with Operational Fallbacks & Quality Controls:
  - G-13: Hard unit-range check (Creatinine mmol/L -> mg/dL conversion)
  - G-01/G-02: Operational BP fallback (distinct visit dates / severe recheck)
  - EC-11: Missingness semantics ('NOT_DOCUMENTED', 'NOT_DONE', 'UNKNOWN')
  - DV-26: Evidence Completeness Score (0.0 to 1.0)
  - DV-27: Certainty Gate condition (Score == 1.0 required for DEFINITE)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict, Tuple
import math

RULE_VERSION = "ISSHP-2021-v1.2"

# ── Reference ranges and thresholds ───────────────────────────────────────
BP_HTN_SBP = 140           # mmHg
BP_HTN_DBP = 90            # mmHg
BP_SEVERE_SBP = 160        # mmHg
BP_SEVERE_DBP = 110        # mmHg
BP_MIN_INTERVAL_HOURS = 4  # Hours between confirming readings

UPCR_THRESHOLD = 0.3       # g/g
UPCR_MG_MMOL_THRESHOLD = 30 # mg/mmol equivalent
PROT_24H_THRESHOLD = 300   # mg/24h
DIPSTICK_THRESHOLD = 2     # 2+ (coded as integer)

PLATELET_THRESHOLD = 100        # x10³/µL — ISSHP criterion
CREATININE_THRESHOLD = 1.1      # mg/dL
CREATININE_BASELINE_MULTIPLIER = 2.0

AST_ULN = 40               # U/L
ALT_ULN = 35               # U/L
LDH_ULN = 250              # U/L

GA_EOPE_CUTOFF_WEEKS = 34  # <34+0 = EOPE, ≥34+0 = LOPE

# Missingness constants (EC-11)
NOT_DOCUMENTED = "NOT_DOCUMENTED"
NOT_DONE = "NOT_DONE"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

DIPSTICK_MAP = {"trace": 0.5, "1+": 1, "2+": 2, "3+": 3, "4+": 4}


@dataclass
class CriterionResult:
    criterion_id: str
    criterion_name: str
    met: bool
    formula: str
    inputs: dict
    source_fields: list
    first_date_met: Optional[datetime] = None
    gestational_age_at_event: Optional[str] = None
    rule_version: str = RULE_VERSION
    missingness_status: Optional[str] = None
    notes: str = ""


# ── G-13: Hard Unit-Range Check for Creatinine ─────────────────────────────

def validate_and_convert_creatinine(value: Any, unit: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
    """
    G-13: Hard Range Check per Analyte-Unit Pair.
    13% of trial creatinine results are incorrectly labeled as 'mmol/L' or reported in umol/L.
    Normal serum creatinine in pregnancy: 0.4 - 0.9 mg/dL (35 - 80 umol/L).
    If creatinine > 10.0 or unit is 'mmol/L'/'umol/L', convert (value / 88.42) to mg/dL.
    """
    if value is None or str(value).strip().upper() in (NOT_DOCUMENTED, NOT_DONE, UNKNOWN, ""):
        return None, NOT_DOCUMENTED

    try:
        val = float(value)
    except (ValueError, TypeError):
        return None, NOT_DOCUMENTED

    unit_clean = str(unit).strip().lower() if unit else ""

    # Hard range check: if val > 10.0 or unit contains mmol/umol, it is in umol/L (or mislabeled mmol/L)
    if val > 10.0 or "mmol" in unit_clean or "umol" in unit_clean or "µmol" in unit_clean:
        converted = val / 88.42
        return round(converted, 2), "UNIT_ERROR_CONVERTED_UMOL_TO_MGDL"

    return round(val, 2), "VALID"


# ── Gestational age utilities ──────────────────────────────────────────────

def ga_to_days(ga_str: str) -> int:
    try:
        parts = ga_str.strip().split("+")
        weeks = int(parts[0])
        days = int(parts[1]) if len(parts) > 1 else 0
        return weeks * 7 + days
    except Exception:
        raise ValueError(f"Invalid GA format: {ga_str!r}. Expected 'WW+D'.")


def parse_dipstick(value: Any) -> Optional[float]:
    if value is None or str(value).strip().upper() in (NOT_DOCUMENTED, NOT_DONE, UNKNOWN, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    normalized = str(value).strip().lower()
    return DIPSTICK_MAP.get(normalized)


# ── HTN-01: Qualifying hypertension (with G-01/G-02 Operational Fallback) ──

def derive_htn_01(bp_readings: List[dict]) -> CriterionResult:
    """
    HTN-01: Hypertension ≥140/90 mmHg on at least 2 occasions.
    G-01 / G-02 Operational Fallback:
    1. If timestamps available: confirm pair ≥ 4 hours apart.
    2. If timestamps absent: fall back to 2 readings at distinct visit dates, OR
    3. Severe range BP (≥160/110) plus recheck within same visit.
    """
    if not bp_readings:
        return CriterionResult(
            criterion_id="HTN-01",
            criterion_name="Qualifying hypertension (≥140/90 mmHg)",
            met=False,
            formula="SBP ≥140 OR DBP ≥90 on ≥2 occasions (≥4h apart or distinct visit dates)",
            inputs={"bp_readings_count": 0},
            source_fields=[],
            missingness_status=NOT_DOCUMENTED,
            notes="No BP readings documented in EDC or eSource.",
        )

    qualifying = [
        r for r in bp_readings
        if isinstance(r.get("sbp"), (int, float)) and isinstance(r.get("dbp"), (int, float))
        and (r["sbp"] >= BP_HTN_SBP or r["dbp"] >= BP_HTN_DBP)
    ]

    if len(qualifying) < 2:
        return CriterionResult(
            criterion_id="HTN-01",
            criterion_name="Qualifying hypertension (≥140/90 mmHg)",
            met=False,
            formula="SBP ≥140 OR DBP ≥90 on ≥2 occasions",
            inputs={"qualifying_count": len(qualifying)},
            source_fields=[r.get("source", "") for r in bp_readings],
            notes=f"Only {len(qualifying)} qualifying reading found. Need ≥2.",
        )

    # Strategy A: Check timestamps if available
    timed_readings = [r for r in qualifying if isinstance(r.get("datetime"), datetime)]
    if len(timed_readings) >= 2:
        timed_sorted = sorted(timed_readings, key=lambda r: r["datetime"])
        for i in range(len(timed_sorted)):
            for j in range(i + 1, len(timed_sorted)):
                t1, t2 = timed_sorted[i]["datetime"], timed_sorted[j]["datetime"]
                interval_hours = (t2 - t1).total_seconds() / 3600
                if interval_hours >= BP_MIN_INTERVAL_HOURS:
                    return CriterionResult(
                        criterion_id="HTN-01",
                        criterion_name="Qualifying hypertension (≥140/90 mmHg, ≥4h apart)",
                        met=True,
                        formula=f"SBP ≥140 OR DBP ≥90 confirmed ≥4h apart ({round(interval_hours, 1)}h)",
                        inputs={"reading_1": f"{timed_sorted[i]['sbp']}/{timed_sorted[i]['dbp']}", "reading_2": f"{timed_sorted[j]['sbp']}/{timed_sorted[j]['dbp']}"},
                        source_fields=[timed_sorted[i].get("source", ""), timed_sorted[j].get("source", "")],
                        first_date_met=t1,
                    )

    # Strategy B: Operational Fallback G-01/G-02 — Distinct Visit Dates
    visit_dates = set(r.get("date", str(r.get("datetime", "")))[:10] for r in qualifying)
    if len(visit_dates) >= 2:
        return CriterionResult(
            criterion_id="HTN-01",
            criterion_name="Qualifying hypertension (Operational Fallback: Distinct Visit Dates)",
            met=True,
            formula="SBP ≥140 OR DBP ≥90 on 2 distinct visit dates (G-01/G-02 Fallback Rule)",
            inputs={"qualifying_dates": list(visit_dates)},
            source_fields=[r.get("source", "") for r in qualifying],
            notes="Confirmed via operational fallback: qualifying readings on distinct visit dates.",
        )

    # Strategy C: Severe range BP plus recheck within one visit
    severe_readings = [r for r in qualifying if r["sbp"] >= BP_SEVERE_SBP or r["dbp"] >= BP_SEVERE_DBP]
    if len(severe_readings) >= 1 and len(qualifying) >= 2:
        return CriterionResult(
            criterion_id="HTN-01",
            criterion_name="Qualifying hypertension (Operational Fallback: Severe Range + Recheck)",
            met=True,
            formula="Severe BP (≥160/110) + repeat recheck within same visit (G-02 Fallback Rule)",
            inputs={"severe_reading": f"{severe_readings[0]['sbp']}/{severe_readings[0]['dbp']}"},
            source_fields=[r.get("source", "") for r in qualifying],
        )

    return CriterionResult(
        criterion_id="HTN-01",
        criterion_name="Qualifying hypertension (≥140/90 mmHg)",
        met=False,
        formula="SBP ≥140 OR DBP ≥90 on ≥2 occasions",
        inputs={"qualifying_count": len(qualifying)},
        source_fields=[r.get("source", "") for r in bp_readings],
        notes="Qualifying readings present but unconfirmed across 4h or distinct visit dates.",
    )


# ── HTN-02: Severe-range hypertension ─────────────────────────────────────

def derive_htn_02(bp_readings: List[dict]) -> CriterionResult:
    severe = [
        r for r in bp_readings
        if (r.get("sbp", 0) or 0) >= BP_SEVERE_SBP or (r.get("dbp", 0) or 0) >= BP_SEVERE_DBP
    ]
    if severe:
        worst = max(severe, key=lambda r: (r.get("sbp") or 0) + (r.get("dbp") or 0))
        return CriterionResult(
            criterion_id="HTN-02",
            criterion_name=f"Severe-range hypertension (≥{BP_SEVERE_SBP}/{BP_SEVERE_DBP} mmHg)",
            met=True,
            formula=f"Any reading SBP ≥{BP_SEVERE_SBP} OR DBP ≥{BP_SEVERE_DBP} mmHg",
            inputs={"worst_bp": f"{worst['sbp']}/{worst['dbp']} mmHg"},
            source_fields=[worst.get("source", "")],
            first_date_met=worst.get("datetime"),
        )
    return CriterionResult(
        criterion_id="HTN-02",
        criterion_name=f"Severe-range hypertension (≥{BP_SEVERE_SBP}/{BP_SEVERE_DBP} mmHg)",
        met=False,
        formula=f"Any reading SBP ≥{BP_SEVERE_SBP} OR DBP ≥{BP_SEVERE_DBP} mmHg",
        inputs={"readings_count": len(bp_readings)},
        source_fields=[],
        missingness_status=NOT_DOCUMENTED if not bp_readings else None,
    )


# ── PROT-01: Proteinuria ───────────────────────────────────────────────────

def derive_prot_01(
    upcr: Optional[float] = None,
    dipstick_raw: Any = None,
    prot_24h_mg: Optional[float] = None,
    source: str = "LIMS",
) -> CriterionResult:
    dipstick = parse_dipstick(dipstick_raw)
    inputs = {"upcr_g_g": upcr, "dipstick": dipstick_raw, "prot_24h_mg": prot_24h_mg}

    if upcr is not None:
        met = upcr >= UPCR_THRESHOLD
        return CriterionResult(
            criterion_id="PROT-01",
            criterion_name=f"Proteinuria (UPCR ≥{UPCR_THRESHOLD} g/g)",
            met=met,
            formula=f"UPCR ≥{UPCR_THRESHOLD} g/g [preferred method]",
            inputs=inputs,
            source_fields=[source],
        )

    if dipstick is not None:
        met = dipstick >= DIPSTICK_THRESHOLD
        return CriterionResult(
            criterion_id="PROT-01",
            criterion_name=f"Proteinuria (Dipstick ≥{DIPSTICK_THRESHOLD}+)",
            met=met,
            formula=f"Dipstick ≥{DIPSTICK_THRESHOLD}+ (UPCR unavailable)",
            inputs=inputs,
            source_fields=[source],
            notes="UPCR absent; dipstick used per protocol fallback G-06.",
        )

    if prot_24h_mg is not None:
        met = prot_24h_mg >= PROT_24H_THRESHOLD
        return CriterionResult(
            criterion_id="PROT-01",
            criterion_name=f"Proteinuria (24h urine ≥{PROT_24H_THRESHOLD} mg)",
            met=met,
            formula=f"24h urine protein ≥{PROT_24H_THRESHOLD} mg/24h",
            inputs=inputs,
            source_fields=[source],
        )

    return CriterionResult(
        criterion_id="PROT-01",
        criterion_name="Proteinuria assessment",
        met=False,
        formula="UPCR ≥0.3 g/g OR Dipstick ≥2+ OR 24h protein ≥300mg",
        inputs=inputs,
        source_fields=[source],
        missingness_status=NOT_DOCUMENTED,
        notes="No proteinuria result documented.",
    )


# ── HAEM-01: Thrombocytopenia ──────────────────────────────────────────────

def derive_haem_01(platelet_count: Optional[float], source: str = "LIMS") -> CriterionResult:
    if platelet_count is None:
        return CriterionResult(
            criterion_id="HAEM-01",
            criterion_name=f"Thrombocytopenia (platelets <{PLATELET_THRESHOLD} x10³/µL)",
            met=False,
            formula=f"Platelet count <{PLATELET_THRESHOLD} x10³/µL",
            inputs={"platelet_count": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )

    met = platelet_count < PLATELET_THRESHOLD
    return CriterionResult(
        criterion_id="HAEM-01",
        criterion_name=f"Thrombocytopenia (platelets <{PLATELET_THRESHOLD} x10³/µL)",
        met=met,
        formula=f"Platelet count <{PLATELET_THRESHOLD} x10³/µL",
        inputs={"platelet_count": platelet_count},
        source_fields=[source],
    )


# ── RENAL-01: Renal impairment (with G-13 Unit Check) ────────────────────

def derive_renal_01(
    creatinine_raw: Any = None,
    unit_raw: Optional[str] = None,
    baseline_creatinine: Optional[float] = None,
    source: str = "LIMS",
    # Backward-compat alias: old tests call derive_renal_01(creatinine=X)
    creatinine: Any = None,
) -> CriterionResult:
    # Support legacy keyword arg
    if creatinine_raw is None and creatinine is not None:
        creatinine_raw = creatinine

    val, unit_flag = validate_and_convert_creatinine(creatinine_raw, unit_raw)

    ratio_vs_baseline = None
    if val is not None and baseline_creatinine and baseline_creatinine > 0:
        ratio_vs_baseline = round(val / baseline_creatinine, 2)

    inputs = {
        "creatinine_raw": creatinine_raw,
        "creatinine_converted_mg_dL": val,
        "unit_flag": unit_flag,
        "baseline_creatinine": baseline_creatinine,
        "ratio_vs_baseline": ratio_vs_baseline,
    }

    if val is None:
        return CriterionResult(
            criterion_id="RENAL-01",
            criterion_name="Renal impairment (creatinine >1.1 mg/dL)",
            met=False,
            formula=f"Creatinine >{CREATININE_THRESHOLD} mg/dL",
            inputs=inputs,
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )

    absolute_met = val > CREATININE_THRESHOLD
    baseline_met = ratio_vs_baseline is not None and ratio_vs_baseline >= CREATININE_BASELINE_MULTIPLIER
    met = absolute_met or baseline_met

    return CriterionResult(
        criterion_id="RENAL-01",
        criterion_name="Renal impairment (creatinine >1.1 mg/dL or ≥2× baseline)",
        met=met,
        formula=f"Creatinine >{CREATININE_THRESHOLD} mg/dL OR ≥2× baseline",
        inputs=inputs,
        source_fields=[source],
        notes=f"Unit check: {unit_flag}. Converted value: {creatinine} mg/dL.",
    )


# ── HEP-01: Hepatic dysfunction ────────────────────────────────────────────

def derive_hep_01(ast: Optional[float] = None, alt: Optional[float] = None, source: str = "LIMS") -> CriterionResult:
    if ast is None and alt is None:
        return CriterionResult(
            criterion_id="HEP-01",
            criterion_name="Hepatic dysfunction (AST or ALT >2× ULN)",
            met=False,
            formula=f"AST >{2*AST_ULN} U/L OR ALT >{2*ALT_ULN} U/L",
            inputs={"ast": None, "alt": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )

    ast_met = ast is not None and (ast / AST_ULN) > 2.0
    alt_met = alt is not None and (alt / ALT_ULN) > 2.0
    met = ast_met or alt_met

    return CriterionResult(
        criterion_id="HEP-01",
        criterion_name="Hepatic dysfunction (AST or ALT >2x ULN)",
        met=met,
        formula=f"AST >{2*AST_ULN} U/L OR ALT >{2*ALT_ULN} U/L",
        inputs={
            "ast": ast, "alt": alt,
            "ast_x_uln": round(ast / AST_ULN, 2) if ast is not None else None,
            "alt_x_uln": round(alt / ALT_ULN, 2) if alt is not None else None,
        },
        source_fields=[source],
    )


# ── HEP-02: LDH elevation ─────────────────────────────────────────────────

def derive_hep_02(ldh: Optional[float] = None, source: str = "LIMS") -> CriterionResult:
    threshold = 2 * LDH_ULN
    if ldh is None:
        return CriterionResult(
            criterion_id="HEP-02",
            criterion_name=f"LDH elevation (>{threshold} U/L)",
            met=False,
            formula=f"LDH >{threshold} U/L (>2× ULN)",
            inputs={"ldh": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )
    met = ldh > threshold
    return CriterionResult(
        criterion_id="HEP-02",
        criterion_name=f"LDH elevation (>{threshold} U/L)",
        met=met,
        formula=f"LDH >{threshold} U/L (>2× ULN)",
        inputs={"ldh": ldh, "ldh_x_uln": round(ldh / LDH_ULN, 2)},
        source_fields=[source],
    )


# ── FGR-01: Fetal Growth Restriction ──────────────────────────────────────

FGR_CENTILE_THRESHOLD = 10

def derive_fgr_01(efw_centile: Optional[float], source: str = "USS") -> CriterionResult:
    if efw_centile is None:
        return CriterionResult(
            criterion_id="FGR-01",
            criterion_name=f"Fetal growth restriction (EFW <{FGR_CENTILE_THRESHOLD}th centile)",
            met=False,
            formula=f"EFW <{FGR_CENTILE_THRESHOLD}th centile on USS",
            inputs={"efw_centile": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )
    met = efw_centile < FGR_CENTILE_THRESHOLD
    return CriterionResult(
        criterion_id="FGR-01",
        criterion_name=f"Fetal growth restriction (EFW <{FGR_CENTILE_THRESHOLD}th centile)",
        met=met,
        formula=f"EFW <{FGR_CENTILE_THRESHOLD}th centile on USS",
        inputs={"efw_centile": efw_centile},
        source_fields=[source],
    )


# ── DOPP-01: Abnormal Doppler ──────────────────────────────────────────────

def derive_dopp_01(ua_aedf: Optional[bool] = None, ua_redf: Optional[bool] = None, source: str = "USS") -> CriterionResult:
    if ua_aedf is None and ua_redf is None:
        return CriterionResult(
            criterion_id="DOPP-01",
            criterion_name="Abnormal umbilical artery Doppler (AEDF/REDF)",
            met=False,
            formula="Absent or reversed end-diastolic flow in umbilical artery",
            inputs={"ua_aedf": None, "ua_redf": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )
    met = bool(ua_aedf) or bool(ua_redf)
    return CriterionResult(
        criterion_id="DOPP-01",
        criterion_name="Abnormal umbilical artery Doppler (AEDF/REDF)",
        met=met,
        formula="Absent or reversed end-diastolic flow in umbilical artery",
        inputs={"ua_aedf": ua_aedf, "ua_redf": ua_redf},
        source_fields=[source],
    )


# ── ONSET-01: Onset Classification (EOPE / LOPE) ──────────────────────────

def days_to_ga(days: int) -> str:
    return f"{days // 7}+{days % 7}"

def derive_onset_class(ga_at_first_criterion: str) -> CriterionResult:
    try:
        days = ga_to_days(ga_at_first_criterion)
        is_eope = days < ga_to_days(f"{GA_EOPE_CUTOFF_WEEKS}+0")
        classification = "EOPE" if is_eope else "LOPE"
        return CriterionResult(
            criterion_id="ONSET-01",
            criterion_name=f"Onset classification ({classification})",
            met=is_eope,
            formula=f"GA at first criterion <{GA_EOPE_CUTOFF_WEEKS}+0 weeks → EOPE, else LOPE",
            inputs={"ga": ga_at_first_criterion, "classification": classification, "ga_days": days},
            source_fields=["EDC"],
        )
    except ValueError:
        return CriterionResult(
            criterion_id="ONSET-01",
            criterion_name="Onset classification",
            met=False,
            formula="Invalid GA format",
            inputs={"ga": ga_at_first_criterion},
            source_fields=[],
            missingness_status=NOT_DOCUMENTED,
        )


# ── COMP-01: HELLP Composite ───────────────────────────────────────────────

def derive_hellp_composite(
    haem_result: CriterionResult,
    hep1_result: CriterionResult,
    hep2_result: CriterionResult,
    platelet_count: Optional[float] = None,
) -> CriterionResult:
    hematologic = haem_result.met
    hepatic = hep1_result.met or hep2_result.met
    met = hematologic and hepatic
    return CriterionResult(
        criterion_id="COMP-01",
        criterion_name="HELLP Syndrome (hematologic + hepatic criteria)",
        met=met,
        formula="Thrombocytopenia <100 AND (AST/ALT >2×ULN OR LDH >2×ULN)",
        inputs={
            "haematologic_met": hematologic,
            "hepatic_met": hepatic,
            "platelet_count": platelet_count,
        },
        source_fields=["LIMS"],
    )


# ── SEV-01: Severity Assessment ────────────────────────────────────────────

def derive_severity(criteria: dict) -> CriterionResult:
    severe_ids = ["HTN-02", "HAEM-01", "RENAL-01", "HEP-01", "HEP-02", "FGR-01", "DOPP-01", "COMP-01"]
    met_severe = [sid for sid in severe_ids if sid in criteria and criteria[sid].met]
    met = len(met_severe) > 0
    return CriterionResult(
        criterion_id="SEV-01",
        criterion_name="Severe features present",
        met=met,
        formula=f"Any of: {', '.join(severe_ids)}",
        inputs={"severe_criteria_met": met_severe, "count": len(met_severe)},
        source_fields=[],
    )


# ── ECLAMP-01, ABRUPT-01, MGSO4-01 (G-03, G-04, G-05) ──────────────────────

def derive_eclamp_01(seizure_documented: Any, source: str = "EDC/eSource") -> CriterionResult:
    """G-03: Eclampsia (witnessed seizure)."""
    if seizure_documented is None or str(seizure_documented).upper() in (NOT_DOCUMENTED, ""):
        return CriterionResult(
            criterion_id="ECLAMP-01",
            criterion_name="Eclampsia (generalized seizure)",
            met=False,
            formula="Documented generalized seizure in patient with preeclampsia",
            inputs={"seizure_documented": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )
    met = str(seizure_documented).lower() in ("true", "yes", "1", "witnessed")
    return CriterionResult(
        criterion_id="ECLAMP-01",
        criterion_name="Eclampsia (generalized seizure)",
        met=met,
        formula="Documented generalized seizure in patient with preeclampsia",
        inputs={"seizure_documented": seizure_documented},
        source_fields=[source],
    )


def derive_mgso4_01(mgso4_exposure: Any, source: str = "eSource") -> CriterionResult:
    """G-05: True Magnesium Sulfate exposure."""
    if mgso4_exposure is None or str(mgso4_exposure).upper() in (NOT_DOCUMENTED, ""):
        return CriterionResult(
            criterion_id="MGSO4-01",
            criterion_name="Magnesium Sulfate IV exposure",
            met=False,
            formula="Intravenous MgSO4 administered for seizure prophylaxis/treatment",
            inputs={"mgso4_exposure": None},
            source_fields=[source],
            missingness_status=NOT_DOCUMENTED,
        )
    met = str(mgso4_exposure).lower() in ("true", "yes", "1", "iv_mgso4")
    return CriterionResult(
        criterion_id="MGSO4-01",
        criterion_name="Magnesium Sulfate IV exposure",
        met=met,
        formula="Intravenous MgSO4 administered for seizure prophylaxis/treatment",
        inputs={"mgso4_exposure": mgso4_exposure},
        source_fields=[source],
    )


# ── DV-26: Evidence Completeness Score (0.0 to 1.0) ───────────────────────

def derive_evidence_completeness(case_data: dict) -> Tuple[float, List[str]]:
    """
    DV-26: Evidence Completeness Module.
    Calculates a score between 0.0 and 1.0 based on presence of 5 required evidence anchors:
      1. Dating anchor (1st trimester scan or LMP) [0.20]
      2. BP trajectory (>= 2 SBP/DBP readings) [0.20]
      3. Proteinuria result (UPCR or dipstick) [0.20]
      4. Organ dysfunction labs (Platelets, Creatinine, AST/ALT) [0.20]
      5. Fetal growth / Doppler assessment [0.20]

    Returns:
        (score: float, missing_anchors: List[str])
    """
    missing = []
    points = 0.0

    # 1. Dating anchor
    if case_data.get("firstUssDate") or case_data.get("lnmp") or case_data.get("edd"):
        points += 0.20
    else:
        missing.append("Dating Anchor (First-trimester USS or LMP missing)")

    # 2. BP trajectory
    bp_list = case_data.get("bp_readings", case_data.get("bpLog", []))
    if len(bp_list) >= 2:
        points += 0.20
    else:
        missing.append("BP Trajectory (At least 2 serial BP readings required)")

    # 3. Proteinuria
    if case_data.get("upcr") is not None or case_data.get("dipstick_raw") is not None or case_data.get("proteinuriaLog"):
        points += 0.20
    else:
        missing.append("Proteinuria Assessment (UPCR or dipstick missing)")

    # 4. Organ dysfunction labs
    labs = case_data.get("labLog", [])
    has_platelets = case_data.get("platelet_count") is not None or any(l.get("analyte") == "Platelet Count" for l in labs)
    has_creatinine = case_data.get("creatinine") is not None or case_data.get("creatinine_raw") is not None or any(l.get("analyte") == "Creatinine" for l in labs)
    if has_platelets and has_creatinine:
        points += 0.20
    else:
        missing.append("Organ Dysfunction Labs (Platelets or Creatinine panel missing)")

    # 5. Fetal assessment
    if case_data.get("efw_centile") is not None or case_data.get("ua_aedf") or case_data.get("sourceDocs", {}).get("ultrasound"):
        points += 0.20
    else:
        missing.append("Fetal Growth & Doppler Assessment (Ultrasound report missing)")

    return round(points, 2), missing


# ── Full Case Derivation Runner ────────────────────────────────────────────

def run_full_derivation(case_data: dict) -> dict:
    """
    Run all criteria and calculate DV-26 Evidence Completeness Score + DV-27 Certainty Gate.
    """
    bp = case_data.get("bp_readings", case_data.get("bpLog", []))

    results: Dict[str, CriterionResult] = {}
    results["HTN-01"] = derive_htn_01(bp)
    results["HTN-02"] = derive_htn_02(bp)
    results["PROT-01"] = derive_prot_01(
        upcr=case_data.get("upcr"),
        dipstick_raw=case_data.get("dipstick_raw"),
        prot_24h_mg=case_data.get("prot_24h_mg"),
    )
    results["HAEM-01"] = derive_haem_01(case_data.get("platelet_count"))
    results["RENAL-01"] = derive_renal_01(
        creatinine_raw=case_data.get("creatinine_raw", case_data.get("creatinine")),
        unit_raw=case_data.get("creatinine_unit"),
        baseline_creatinine=case_data.get("baseline_creatinine"),
    )
    results["HEP-01"] = derive_hep_01(ast=case_data.get("ast"), alt=case_data.get("alt"))
    results["HEP-02"] = derive_hep_02(ldh=case_data.get("ldh"))
    results["FGR-01"] = derive_fgr_01(efw_centile=case_data.get("efw_centile"))
    results["DOPP-01"] = derive_dopp_01(
        ua_aedf=case_data.get("ua_aedf"),
        ua_redf=case_data.get("ua_redf"),
    )
    results["COMP-01"] = derive_hellp_composite(
        haem_result=results["HAEM-01"],
        hep1_result=results["HEP-01"],
        hep2_result=results["HEP-02"],
        platelet_count=case_data.get("platelet_count"),
    )
    results["SEV-01"] = derive_severity(results)
    results["ONSET-01"] = derive_onset_class(case_data.get("ga_at_first_criterion", "38+0"))
    results["ECLAMP-01"] = derive_eclamp_01(case_data.get("seizure_documented"))
    results["MGSO4-01"] = derive_mgso4_01(case_data.get("mgso4_exposure"))

    # DV-26: Evidence Completeness Score
    score, missing_anchors = derive_evidence_completeness(case_data)

    # DV-27: Certainty Gate condition
    certainty_gate_passed = (score == 1.0)

    return {
        **results,
        "evidence_completeness_score": score,
        "missing_anchors": missing_anchors,
        "certainty_gate_passed": certainty_gate_passed,
        "rule_version": RULE_VERSION,
    }


