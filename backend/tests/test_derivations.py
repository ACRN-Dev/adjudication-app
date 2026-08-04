"""
Unit Tests — Clinical Derivation Engine
==========================================
Tests all 14 ISSHP 2021 diagnostic criteria against:
  - Reference positive cases (ZWE001-0292, ZWE001-0443 archetypes)
  - Boundary values (edge cases at exact threshold)
  - Negative cases (normal values)
  - Missing data (None inputs)
  - resolve_value() source hierarchy

Run with: pytest tests/test_derivations.py -v
"""

from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.derivation_engine import (
    derive_htn_01, derive_htn_02, derive_prot_01, derive_haem_01,
    derive_renal_01, derive_hep_01, derive_hep_02, derive_fgr_01,
    derive_dopp_01, derive_onset_class, derive_hellp_composite,
    derive_severity, run_full_derivation,
    ga_to_days, days_to_ga, parse_dipstick,
    RULE_VERSION,
)
from services.resolve_value import resolve_value, DiscrepancyCategory


# ── Fixtures ───────────────────────────────────────────────────────────────

T0 = datetime(2026, 7, 4, 8, 14)   # First severe BP reading
T1 = T0 + timedelta(hours=4, minutes=26)  # Second reading (4h26m later)
T_BASELINE = T0 - timedelta(days=21)

BP_SEVERE_PAIR = [
    {"sbp": 162, "dbp": 112, "datetime": T0,  "source": "eSource Vitals"},
    {"sbp": 168, "dbp": 114, "datetime": T1,  "source": "eSource Vitals (Repeat)"},
]

BP_MILD_PAIR = [
    {"sbp": 144, "dbp": 92,  "datetime": T0,                           "source": "EDC Visit"},
    {"sbp": 146, "dbp": 94,  "datetime": T0 + timedelta(hours=5),      "source": "EDC Visit"},
]

BP_TOO_CLOSE = [
    {"sbp": 145, "dbp": 95, "datetime": T0,                            "source": "EDC"},
    {"sbp": 148, "dbp": 97, "datetime": T0 + timedelta(hours=2),       "source": "EDC"},
]


# ── Utility tests ──────────────────────────────────────────────────────────

def test_ga_to_days_standard():
    assert ga_to_days("31+2") == 219

def test_ga_to_days_no_day():
    assert ga_to_days("34+0") == 238

def test_days_to_ga():
    assert days_to_ga(219) == "31+2"

def test_parse_dipstick_string():
    assert parse_dipstick("2+") == 2.0
    assert parse_dipstick("3+") == 3.0
    assert parse_dipstick("trace") == 0.5

def test_parse_dipstick_numeric():
    assert parse_dipstick(2) == 2.0

def test_parse_dipstick_none():
    assert parse_dipstick(None) is None


# ── HTN-01 ─────────────────────────────────────────────────────────────────

def test_htn_01_positive_severe_pair():
    """ZWE001-0292 archetype: 162/112 and 168/114, 4h26m apart."""
    r = derive_htn_01(BP_SEVERE_PAIR)
    assert r.met is True
    assert r.criterion_id == "HTN-01"
    assert r.rule_version == RULE_VERSION
    assert r.first_date_met == T0

def test_htn_01_positive_mild_pair():
    """Mild hypertension ≥140/90 confirmed ≥4h apart."""
    r = derive_htn_01(BP_MILD_PAIR)
    assert r.met is True

def test_htn_01_negative_too_close():
    """Two qualifying readings but only 2h apart — not confirmed."""
    r = derive_htn_01(BP_TOO_CLOSE)
    assert r.met is False

def test_htn_01_negative_single_reading():
    """Only one qualifying reading."""
    r = derive_htn_01([BP_SEVERE_PAIR[0]])
    assert r.met is False

def test_htn_01_negative_normal_bp():
    """Normal BP throughout."""
    normal = [{"sbp": 118, "dbp": 74, "datetime": T0, "source": "EDC"}]
    r = derive_htn_01(normal)
    assert r.met is False

def test_htn_01_empty():
    r = derive_htn_01([])
    assert r.met is False


# ── HTN-02 ─────────────────────────────────────────────────────────────────

def test_htn_02_positive():
    r = derive_htn_02(BP_SEVERE_PAIR)
    assert r.met is True

def test_htn_02_negative_mild():
    r = derive_htn_02(BP_MILD_PAIR)
    assert r.met is False

def test_htn_02_boundary_exactly_160():
    """SBP exactly 160 = severe."""
    bp = [{"sbp": 160, "dbp": 90, "datetime": T0, "source": "EDC"}]
    r = derive_htn_02(bp)
    assert r.met is True

def test_htn_02_boundary_159():
    """SBP 159 = NOT severe."""
    bp = [{"sbp": 159, "dbp": 90, "datetime": T0, "source": "EDC"}]
    r = derive_htn_02(bp)
    assert r.met is False


# ── PROT-01 ────────────────────────────────────────────────────────────────

def test_prot_01_upcr_positive():
    r = derive_prot_01(upcr=1.84)
    assert r.met is True
    assert "UPCR" in r.formula

def test_prot_01_upcr_boundary_exactly_0_3():
    r = derive_prot_01(upcr=0.3)
    assert r.met is True

def test_prot_01_upcr_boundary_below():
    r = derive_prot_01(upcr=0.29)
    assert r.met is False

def test_prot_01_dipstick_2plus():
    """Dipstick ≥2+ is positive when UPCR absent."""
    r = derive_prot_01(dipstick_raw="2+")
    assert r.met is True

def test_prot_01_dipstick_1plus_negative():
    r = derive_prot_01(dipstick_raw="1+")
    assert r.met is False

def test_prot_01_prot_24h_positive():
    r = derive_prot_01(prot_24h_mg=450)
    assert r.met is True

def test_prot_01_no_data():
    r = derive_prot_01()
    assert r.met is False

def test_prot_01_upcr_takes_priority_over_dipstick():
    """UPCR <0.3 should override positive dipstick."""
    r = derive_prot_01(upcr=0.20, dipstick_raw="3+")
    assert r.met is False
    assert "UPCR" in r.formula


# ── HAEM-01 ────────────────────────────────────────────────────────────────

def test_haem_01_positive():
    r = derive_haem_01(platelet_count=92)
    assert r.met is True

def test_haem_01_boundary_exactly_100():
    """Exactly 100 = NOT below threshold (criterion is <100, not ≤100)."""
    r = derive_haem_01(platelet_count=100)
    assert r.met is False

def test_haem_01_boundary_99():
    r = derive_haem_01(platelet_count=99)
    assert r.met is True

def test_haem_01_normal():
    r = derive_haem_01(platelet_count=220)
    assert r.met is False

def test_haem_01_none():
    r = derive_haem_01(None)
    assert r.met is False


# ── RENAL-01 ───────────────────────────────────────────────────────────────

def test_renal_01_absolute_threshold():
    """Creatinine >1.1 mg/dL without baseline."""
    r = derive_renal_01(creatinine=1.31)
    assert r.met is True

def test_renal_01_baseline_multiplier():
    """≥2× baseline even if absolute value normal."""
    r = derive_renal_01(creatinine=1.0, baseline_creatinine=0.45)
    assert r.met is True
    assert r.inputs["ratio_vs_baseline"] >= 2.0

def test_renal_01_normal_with_baseline():
    """1.1× baseline — not sufficient."""
    r = derive_renal_01(creatinine=0.65, baseline_creatinine=0.60)
    assert r.met is False

def test_renal_01_boundary_exactly_1_1():
    """Exactly 1.1 is NOT >1.1 — not met."""
    r = derive_renal_01(creatinine=1.1)
    assert r.met is False

def test_renal_01_boundary_1_11():
    r = derive_renal_01(creatinine=1.11)
    assert r.met is True

def test_renal_01_none():
    r = derive_renal_01(creatinine=None)
    assert r.met is False


# ── HEP-01 ─────────────────────────────────────────────────────────────────

def test_hep_01_ast_elevated():
    """AST >2× ULN (ULN=40, so >80)."""
    r = derive_hep_01(ast=96, alt=38)
    assert r.met is True
    assert r.inputs["ast_x_uln"] > 2.0

def test_hep_01_alt_elevated():
    r = derive_hep_01(ast=38, alt=78)
    assert r.met is True

def test_hep_01_boundary_exactly_2x():
    """AST exactly 2× ULN (=80) — NOT >2×, so not met."""
    r = derive_hep_01(ast=80, alt=30)
    assert r.met is False

def test_hep_01_normal():
    r = derive_hep_01(ast=28, alt=22)
    assert r.met is False

def test_hep_01_none():
    r = derive_hep_01(ast=None, alt=None)
    assert r.met is False


# ── FGR-01 ─────────────────────────────────────────────────────────────────

def test_fgr_01_positive():
    r = derive_fgr_01(efw_centile=6)
    assert r.met is True

def test_fgr_01_boundary_exactly_10():
    """10th centile = NOT below threshold."""
    r = derive_fgr_01(efw_centile=10)
    assert r.met is False

def test_fgr_01_boundary_9():
    r = derive_fgr_01(efw_centile=9)
    assert r.met is True

def test_fgr_01_normal():
    r = derive_fgr_01(efw_centile=55)
    assert r.met is False

def test_fgr_01_none():
    r = derive_fgr_01(None)
    assert r.met is False


# ── DOPP-01 ────────────────────────────────────────────────────────────────

def test_dopp_01_aedf():
    r = derive_dopp_01(ua_aedf=True)
    assert r.met is True

def test_dopp_01_redf():
    r = derive_dopp_01(ua_redf=True)
    assert r.met is True

def test_dopp_01_normal():
    r = derive_dopp_01(ua_aedf=False, ua_redf=False)
    assert r.met is False


# ── ONSET-01 ───────────────────────────────────────────────────────────────

def test_onset_eope():
    """31+2 weeks = EOPE (< 34+0)."""
    r = derive_onset_class("31+2")
    assert r.met is True
    assert r.inputs["classification"] == "EOPE"

def test_onset_lope():
    """36+4 weeks = LOPE (≥ 34+0)."""
    r = derive_onset_class("36+4")
    assert r.inputs["classification"] == "LOPE"

def test_onset_boundary_exactly_34():
    """34+0 weeks = LOPE boundary."""
    r = derive_onset_class("34+0")
    assert r.inputs["classification"] == "LOPE"

def test_onset_boundary_33_6():
    """33+6 weeks = EOPE (one day before cutoff)."""
    r = derive_onset_class("33+6")
    assert r.inputs["classification"] == "EOPE"

def test_onset_invalid_ga():
    r = derive_onset_class("invalid")
    assert r.met is False


# ── COMP-01: HELLP ─────────────────────────────────────────────────────────

def test_hellp_positive():
    haem = derive_haem_01(92)
    hep1 = derive_hep_01(ast=96, alt=78)
    hep2 = derive_hep_02(ldh=None)
    r = derive_hellp_composite(haem, hep1, hep2, platelet_count=92)
    assert r.met is True

def test_hellp_missing_hematologic():
    haem = derive_haem_01(180)  # normal platelets
    hep1 = derive_hep_01(ast=120, alt=100)
    hep2 = derive_hep_02(ldh=600)
    r = derive_hellp_composite(haem, hep1, hep2)
    assert r.met is False

def test_hellp_missing_liver():
    haem = derive_haem_01(85)
    hep1 = derive_hep_01(ast=30, alt=28)
    hep2 = derive_hep_02(ldh=200)
    r = derive_hellp_composite(haem, hep1, hep2)
    assert r.met is False


# ── SEV-01 ─────────────────────────────────────────────────────────────────

def test_severity_with_severe_features():
    """ZWE001-0292 archetype: HTN-02 + HAEM-01 + RENAL-01 all met."""
    criteria = {
        "HTN-02": derive_htn_02(BP_SEVERE_PAIR),
        "HAEM-01": derive_haem_01(92),
        "RENAL-01": derive_renal_01(creatinine_raw=1.31, baseline_creatinine=0.62),
        "HEP-01": derive_hep_01(96, 78),
        "FGR-01": derive_fgr_01(6),
        "DOPP-01": derive_dopp_01(ua_aedf=True),
        "COMP-01": derive_hellp_composite(derive_haem_01(92), derive_hep_01(96,78), derive_hep_02()),
    }
    r = derive_severity(criteria)
    assert r.met is True

def test_severity_without_severe_features():
    """All severe criteria absent."""
    criteria = {
        "HTN-02": derive_htn_02(BP_MILD_PAIR),
        "HAEM-01": derive_haem_01(180),
        "RENAL-01": derive_renal_01(creatinine_raw=0.8),
        "HEP-01": derive_hep_01(25, 22),
        "DOPP-01": derive_dopp_01(),
        "COMP-01": derive_hellp_composite(derive_haem_01(180), derive_hep_01(25,22), derive_hep_02()),
    }
    r = derive_severity(criteria)
    assert r.met is False


# ── Full derivation runner ─────────────────────────────────────────────────

def test_run_full_derivation_zwe001_0292():
    """Full ZWE001-0292 reference case — all severe criteria expected to be met."""
    case = {
        "bp_readings": BP_SEVERE_PAIR,
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine": 1.31,
        "baseline_creatinine": 0.62,
        "ast": 96,
        "alt": 78,
        "ldh": None,
        "efw_centile": 6,
        "ua_aedf": True,
        "ua_redf": False,
        "ga_at_first_criterion": "31+2",
    }
    results = run_full_derivation(case)

    assert results["HTN-01"].met is True
    assert results["HTN-02"].met is True
    assert results["PROT-01"].met is True
    assert results["HAEM-01"].met is True
    assert results["RENAL-01"].met is True
    assert results["HEP-01"].met is True
    assert results["FGR-01"].met is True
    assert results["DOPP-01"].met is True
    assert results["SEV-01"].met is True
    assert results["ONSET-01"].inputs["classification"] == "EOPE"

def test_run_full_derivation_all_normal():
    """Normal case — no criteria should be met."""
    normal_bp = [
        {"sbp": 118, "dbp": 74, "datetime": T0, "source": "EDC"},
        {"sbp": 120, "dbp": 76, "datetime": T1, "source": "EDC"},
    ]
    case = {
        "bp_readings": normal_bp,
        "upcr": 0.1,
        "platelet_count": 220,
        "creatinine": 0.7,
        "baseline_creatinine": 0.65,
        "ast": 22,
        "alt": 18,
        "efw_centile": 55,
        "ua_aedf": False,
        "ua_redf": False,
        "ga_at_first_criterion": "38+2",
    }
    results = run_full_derivation(case)

    assert results["HTN-01"].met is False
    assert results["HTN-02"].met is False
    assert results["PROT-01"].met is False
    assert results["HAEM-01"].met is False
    assert results["RENAL-01"].met is False
    assert results["HEP-01"].met is False
    assert results["FGR-01"].met is False
    assert results["SEV-01"].met is False


# ── resolve_value() unit tests ─────────────────────────────────────────────

def test_resolve_value_edc_wins():
    """EDC present and eSource absent — EDC used."""
    r = resolve_value(edc_value=162, esource_value=None)
    assert r.canonical_value == 162
    assert r.source == "EDC"
    assert r.discrepant is False

def test_resolve_value_esource_fills_gap():
    """EDC absent, eSource present — eSource fills gap."""
    r = resolve_value(edc_value=None, esource_value=160)
    assert r.canonical_value == 160
    assert r.source == "eSource"
    assert r.discrepant is False

def test_resolve_value_concordant():
    """Both present and equal — no discrepancy."""
    r = resolve_value(edc_value=162, esource_value=162)
    assert r.canonical_value == 162
    assert r.discrepant is False
    assert r.discrepancy_category == DiscrepancyCategory.EXACT_MATCH

def test_resolve_value_discrepant_numeric():
    """Both present but different — EDC wins, discrepancy flagged."""
    r = resolve_value(edc_value=140, esource_value=162)
    assert r.canonical_value == 140    # EDC always wins
    assert r.discrepant is True
    assert r.discrepancy_category == DiscrepancyCategory.VALUE_DISCREPANCY

def test_resolve_value_discrepant_clinically_meaningful():
    """Large discrepancy flagged as clinically meaningful."""
    r = resolve_value(edc_value=120, esource_value=180, clinically_meaningful_threshold=20)
    assert r.discrepant is True
    assert r.clinically_meaningful_discrepancy is True

def test_resolve_value_both_none():
    r = resolve_value(edc_value=None, esource_value=None)
    assert r.canonical_value is None
    assert r.source is None

def test_resolve_value_edc_never_overwritten():
    """
    CRITICAL: Even when eSource has a 'better' value,
    EDC must never be silently overwritten.
    """
    r = resolve_value(edc_value=130, esource_value=200)
    assert r.canonical_value == 130    # EDC wins unconditionally
    assert r.source == "EDC"


# ── G-13: Hard Unit-Range Check (Creatinine) ──────────────────────────────

from services.derivation_engine import (
    validate_and_convert_creatinine,
    derive_eclamp_01, derive_mgso4_01,
    derive_evidence_completeness,
    NOT_DOCUMENTED,
)


def test_g13_normal_mg_dl():
    """Valid creatinine in mg/dL — no conversion needed."""
    value, flag = validate_and_convert_creatinine(1.31, "mg/dL")
    assert value == 1.31
    assert flag == "VALID"


def test_g13_creatinine_high_value_triggers_conversion():
    """G-13: Creatinine 120 (>10.0) — interpreted as umol/L, converted to mg/dL."""
    value, flag = validate_and_convert_creatinine(120, "mmol/L")
    assert flag == "UNIT_ERROR_CONVERTED_UMOL_TO_MGDL"
    assert abs(value - 1.36) < 0.01  # 120 / 88.42 = 1.357


def test_g13_creatinine_umol_L_label_triggers_conversion():
    """G-13: Unit labeled umol/L — convert."""
    value, flag = validate_and_convert_creatinine(75, "umol/L")
    assert flag == "UNIT_ERROR_CONVERTED_UMOL_TO_MGDL"
    assert abs(value - 0.85) < 0.01  # 75 / 88.42


def test_g13_creatinine_high_value_no_unit():
    """G-13: Very high value with no unit specified — converted."""
    value, flag = validate_and_convert_creatinine(88.42, None)
    assert flag == "UNIT_ERROR_CONVERTED_UMOL_TO_MGDL"
    assert abs(value - 1.0) < 0.02


def test_g13_creatinine_none():
    """G-13: None input — returns NOT_DOCUMENTED."""
    value, flag = validate_and_convert_creatinine(None, "mg/dL")
    assert value is None
    assert flag == NOT_DOCUMENTED


def test_g13_creatinine_string_blank():
    """G-13: Empty string — returns NOT_DOCUMENTED."""
    value, flag = validate_and_convert_creatinine("", None)
    assert value is None
    assert flag == NOT_DOCUMENTED


def test_g13_renal_01_with_unit_error():
    """G-13: derive_renal_01 receives 120 labeled mmol/L — converts and evaluates correctly."""
    from services.derivation_engine import derive_renal_01
    r = derive_renal_01(creatinine_raw=120, unit_raw="mmol/L")
    assert r.inputs["unit_flag"] == "UNIT_ERROR_CONVERTED_UMOL_TO_MGDL"
    # 120 umol/L = 1.36 mg/dL → >1.1 → met
    assert r.met is True


def test_g13_renal_01_low_value_valid():
    """G-13: Creatinine 0.75 mg/dL — valid, not met."""
    from services.derivation_engine import derive_renal_01
    r = derive_renal_01(creatinine_raw=0.75, unit_raw="mg/dL")
    assert r.inputs["unit_flag"] == "VALID"
    assert r.met is False


# ── G-01/G-02: Operational BP Fallback ────────────────────────────────────

def test_g01_distinct_visit_dates_fallback():
    """G-01: No timestamps, but 2 qualifying readings on distinct visit dates — HTN confirmed."""
    bp = [
        {"sbp": 142, "dbp": 92, "date": "2026-06-10", "source": "eSource"},
        {"sbp": 145, "dbp": 93, "date": "2026-06-17", "source": "eSource"},
    ]
    r = derive_htn_01(bp)
    assert r.met is True
    assert "Distinct Visit Dates" in r.criterion_name or "Fallback" in r.notes or "distinct" in r.formula.lower()


def test_g02_severe_range_recheck_within_visit():
    """G-02: Severe BP (165/115) + recheck in same date — HTN confirmed via severe fallback."""
    bp = [
        {"sbp": 165, "dbp": 115, "date": "2026-07-04", "source": "eSource"},
        {"sbp": 168, "dbp": 112, "date": "2026-07-04", "source": "eSource Recheck"},
    ]
    r = derive_htn_01(bp)
    assert r.met is True


def test_g01_two_readings_same_date_non_severe_not_confirmed():
    """G-01 negative: 2 mild readings same date, no timestamp — cannot confirm."""
    bp = [
        {"sbp": 142, "dbp": 92, "date": "2026-06-10", "source": "eSource"},
        {"sbp": 144, "dbp": 93, "date": "2026-06-10", "source": "eSource"},
    ]
    r = derive_htn_01(bp)
    # Same date, mild range — only severe recheck would pass
    # This should be False unless both readings severe
    assert r.met is False


def test_g01_timestamp_available_takes_priority():
    """G-01: When timestamps present, interval check takes priority over date fallback."""
    bp = [
        {"sbp": 142, "dbp": 92, "datetime": T0, "date": "2026-07-04", "source": "eSource"},
        {"sbp": 145, "dbp": 93, "datetime": T1, "date": "2026-07-04", "source": "eSource"},
    ]
    r = derive_htn_01(bp)
    assert r.met is True  # T1 is 4h26m after T0 — confirmed by timestamp


# ── EC-11: Missingness Semantics ───────────────────────────────────────────

def test_ec11_missing_bp_returns_not_documented():
    """EC-11: Empty BP list returns NOT_DOCUMENTED, never False."""
    r = derive_htn_01([])
    assert r.missingness_status == NOT_DOCUMENTED


def test_ec11_missing_creatinine_returns_not_documented():
    """EC-11: None creatinine returns NOT_DOCUMENTED flag."""
    from services.derivation_engine import derive_renal_01
    r = derive_renal_01(creatinine_raw=None)
    assert r.missingness_status == NOT_DOCUMENTED


def test_ec11_missing_proteinuria_returns_not_documented():
    """EC-11: No proteinuria data returns NOT_DOCUMENTED."""
    r = derive_prot_01()
    assert r.missingness_status == NOT_DOCUMENTED


def test_ec11_missing_labs_returns_not_documented():
    """EC-11: No AST/ALT returns NOT_DOCUMENTED."""
    r = derive_hep_01(ast=None, alt=None)
    assert r.missingness_status == NOT_DOCUMENTED


def test_ec11_missing_eclampsia_returns_not_documented():
    """EC-11: Eclampsia field absent returns NOT_DOCUMENTED."""
    r = derive_eclamp_01(None)
    assert r.missingness_status == NOT_DOCUMENTED


def test_ec11_missing_mgso4_returns_not_documented():
    """EC-11: MgSO4 exposure absent returns NOT_DOCUMENTED."""
    r = derive_mgso4_01(None)
    assert r.missingness_status == NOT_DOCUMENTED


# ── ECLAMP-01 & MGSO4-01 (G-03, G-05) ────────────────────────────────────

def test_eclamp_01_positive():
    r = derive_eclamp_01("yes")
    assert r.met is True

def test_eclamp_01_witnessed():
    r = derive_eclamp_01("witnessed")
    assert r.met is True

def test_eclamp_01_negative():
    r = derive_eclamp_01("no")
    assert r.met is False

def test_eclamp_01_none_not_documented():
    r = derive_eclamp_01(None)
    assert r.met is False
    assert r.missingness_status == NOT_DOCUMENTED


def test_mgso4_01_positive():
    r = derive_mgso4_01("yes")
    assert r.met is True

def test_mgso4_01_iv():
    r = derive_mgso4_01("iv_mgso4")
    assert r.met is True

def test_mgso4_01_negative():
    r = derive_mgso4_01("no")
    assert r.met is False

def test_mgso4_01_none_not_documented():
    r = derive_mgso4_01(None)
    assert r.met is False
    assert r.missingness_status == NOT_DOCUMENTED


# ── DV-26: Evidence Completeness Score ────────────────────────────────────

def test_dv26_full_evidence_score_1_0():
    """DV-26: All 5 anchors present — score == 1.0."""
    case = {
        "firstUssDate": "2025-11-15",
        "bp_readings": [
            {"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"},
            {"sbp": 165, "dbp": 114, "datetime": T1, "source": "eSource"},
        ],
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
    }
    score, missing = derive_evidence_completeness(case)
    assert score == 1.0
    assert missing == []


def test_dv26_no_dating_anchor():
    """DV-26: Missing dating anchor reduces score to 0.80."""
    case = {
        "bp_readings": [
            {"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"},
            {"sbp": 165, "dbp": 114, "datetime": T1, "source": "eSource"},
        ],
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
    }
    score, missing = derive_evidence_completeness(case)
    assert score == 0.80
    assert any("Dating" in m for m in missing)


def test_dv26_missing_proteinuria():
    """DV-26: No proteinuria data reduces score by 0.20."""
    case = {
        "firstUssDate": "2025-11-15",
        "bp_readings": [
            {"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"},
            {"sbp": 165, "dbp": 114, "datetime": T1, "source": "eSource"},
        ],
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
    }
    score, missing = derive_evidence_completeness(case)
    assert score == 0.80
    assert any("Proteinuria" in m for m in missing)


def test_dv26_empty_case_score_0():
    """DV-26: No evidence at all — score == 0.0."""
    score, missing = derive_evidence_completeness({})
    assert score == 0.0
    assert len(missing) == 5


def test_dv26_only_one_bp_reading():
    """DV-26: Only 1 BP reading — BP anchor not satisfied, score penalised."""
    case = {
        "firstUssDate": "2025-11-15",
        "bp_readings": [{"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"}],
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
    }
    score, missing = derive_evidence_completeness(case)
    assert score == 0.80
    assert any("BP" in m for m in missing)


# ── DV-27: Certainty Gate Condition ───────────────────────────────────────

def test_dv27_gate_passed_when_score_1():
    """DV-27: Score 1.0 — DEFINITE certainty option unlocked."""
    case = {
        "firstUssDate": "2025-11-15",
        "bp_readings": [
            {"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"},
            {"sbp": 165, "dbp": 114, "datetime": T1, "source": "eSource"},
        ],
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
    }
    from services.derivation_engine import run_full_derivation
    result = run_full_derivation(case)
    assert result["certainty_gate_passed"] is True


def test_dv27_gate_blocked_when_score_lt_1():
    """DV-27: Score < 1.0 — DEFINITE certainty option BLOCKED."""
    case = {
        "bp_readings": [
            {"sbp": 162, "dbp": 112, "datetime": T0, "source": "eSource"},
            {"sbp": 165, "dbp": 114, "datetime": T1, "source": "eSource"},
        ],
        "upcr": 1.84,
        "platelet_count": 92,
        "creatinine_raw": 1.31,
        "efw_centile": 6,
        # Missing: firstUssDate (dating anchor)
    }
    from services.derivation_engine import run_full_derivation
    result = run_full_derivation(case)
    assert result["certainty_gate_passed"] is False
    assert result["evidence_completeness_score"] == 0.80


def test_dv27_gate_blocked_empty_case():
    """DV-27: Empty case — gate blocked, score 0.0."""
    from services.derivation_engine import run_full_derivation
    result = run_full_derivation({})
    assert result["certainty_gate_passed"] is False
    assert result["evidence_completeness_score"] == 0.0
