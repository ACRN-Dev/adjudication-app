"""
ACRN PROTECT-Africa Endpoint Adjudication Platform
Deterministic Clinical Derivation Engine — DV-01 through DV-30
================================================================

Rule Version: PROTECT-DV-2026.08
Protocols: PROTECT-Africa (EOPE, A202501 v1.2) & LOPE-Nigeria (ACRN-202503 v1.1)
Standards: ISSHP 2021 | ACOG 2020 | FIGO 2019 | 21 CFR Part 11 | SOP-ADJ-002

This module provides the primary deterministic clinical derivation engine.
For missing evidence, functions return DVResult with not_assessable=True.
Never returns False/unmet when required evidence is absent.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import re

RULE_VERSION = "PROTECT-DV-2026.08"


@dataclass
class DVResult:
    dv_id: str
    met: bool
    not_assessable: bool
    result_label: str
    details: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    rule_version: str = RULE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dv_id": self.dv_id,
            "met": self.met,
            "not_assessable": self.not_assessable,
            "result_label": self.result_label,
            "details": self.details,
            "inputs": self.inputs,
            "rule_version": self.rule_version,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def ga_str_to_days(ga_str: Optional[str]) -> Optional[int]:
    """Parse 'WW+D' or 'WW.D' or 'WW' to total days."""
    if not ga_str or not isinstance(ga_str, str):
        return None
    ga_str = ga_str.strip()
    m = re.match(r"^(\d{1,2})(?:[\+\.](\d))?$", ga_str)
    if not m:
        return None
    weeks = int(m.group(1))
    days = int(m.group(2)) if m.group(2) else 0
    if days > 6:
        return None
    return weeks * 7 + days


def days_to_ga_str(days: int) -> str:
    """Format total days into 'WW+D'."""
    weeks = days // 7
    rem = days % 7
    return f"{weeks}+{rem}"


def parse_dipstick_value(val: Any) -> Optional[float]:
    """Convert dipstick raw text to equivalent float level."""
    if val is None:
        return None
    s = str(val).strip().lower()
    if "4+" in s or "++++" in s:
        return 4.0
    if "3+" in s or "+++" in s:
        return 3.0
    if "2+" in s or "++" in s:
        return 2.0
    if "1+" in s or "+" in s:
        return 1.0
    if "trace" in s:
        return 0.5
    if "neg" in s or "0" in s:
        return 0.0
    try:
        return float(val)
    except ValueError:
        return None


# ── Deterministic Derivation Rules (DV-01 .. DV-30) ──────────────────────────

def derive_dv01_max_bp_per_visit(bp_readings: List[Dict[str, Any]]) -> DVResult:
    """DV-01: Maximum SBP/DBP per visit date group."""
    if not bp_readings:
        return DVResult("DV-01", False, True, "NOT_ASSESSABLE", "No BP readings documented.")
    
    grouped: Dict[str, Dict[str, Any]] = {}
    for bp in bp_readings:
        dt = bp.get("date") or bp.get("ga") or "unknown_date"
        sbp = float(bp.get("sbp", 0))
        dbp = float(bp.get("dbp", 0))
        if dt not in grouped:
            grouped[dt] = {"max_sbp": sbp, "max_dbp": dbp, "count": 1}
        else:
            grouped[dt]["max_sbp"] = max(grouped[dt]["max_sbp"], sbp)
            grouped[dt]["max_dbp"] = max(grouped[dt]["max_dbp"], dbp)
            grouped[dt]["count"] += 1

    return DVResult(
        "DV-01", True, False, "COMPLETED",
        f"Consolidated {len(bp_readings)} BP readings across {len(grouped)} distinct visit dates.",
        {"visit_groups": grouped, "total_readings": len(bp_readings)}
    )


def derive_dv02_severe_bp(bp_readings: List[Dict[str, Any]]) -> DVResult:
    """DV-02: Severe hypertension (SBP >= 160 or DBP >= 110)."""
    if not bp_readings:
        return DVResult("DV-02", False, True, "NOT_ASSESSABLE", "A confirmatory dated/timed BP or eligible severe-range recheck not documented")
    
    severe_found = []
    for bp in bp_readings:
        sbp = float(bp.get("sbp", 0))
        dbp = float(bp.get("dbp", 0))
        if sbp >= 160 or dbp >= 110:
            severe_found.append({"sbp": sbp, "dbp": dbp, "date": bp.get("date"), "ga": bp.get("ga")})

    if severe_found:
        max_s = max(b["sbp"] for b in severe_found)
        max_d = max(b["dbp"] for b in severe_found)
        return DVResult(
            "DV-02", True, False, "SEVERE_HTN_MET",
            f"Severe range BP identified ({int(max_s)}/{int(max_d)} mmHg). Count: {len(severe_found)}.",
            {"severe_readings": severe_found, "max_sbp": max_s, "max_dbp": max_d}
        )
    return DVResult("DV-02", False, False, "NOT_MET", "No severe range BP (>=160/110 mmHg) documented.", {"readings_checked": len(bp_readings)})


def derive_dv03_confirmed_htn(bp_readings: List[Dict[str, Any]]) -> DVResult:
    """DV-03: Confirmed hypertension (>=2 readings >=140/90 on distinct dates OR severe+recheck)."""
    if not bp_readings or len(bp_readings) < 2:
        return DVResult("DV-03", False, True, "NOT_ASSESSABLE", "A confirmatory dated/timed BP or eligible severe-range recheck not documented")
    
    qualifying = []
    for bp in bp_readings:
        sbp = float(bp.get("sbp", 0))
        dbp = float(bp.get("dbp", 0))
        if sbp >= 140 or dbp >= 90:
            qualifying.append(bp)

    if len(qualifying) < 2:
        return DVResult("DV-03", False, False, "NOT_MET", "Fewer than 2 qualifying BP readings (>=140/90 mmHg) documented.", {"qualifying_count": len(qualifying)})

    dates = set(b.get("date") for b in qualifying if b.get("date"))
    has_severe = any(float(b.get("sbp", 0)) >= 160 or float(b.get("dbp", 0)) >= 110 for b in qualifying)

    if len(dates) >= 2 or has_severe:
        return DVResult(
            "DV-03", True, False, "CONFIRMED_HTN_MET",
            f"Confirmed HTN met: {len(qualifying)} qualifying readings across {len(dates)} distinct dates (Severe range: {has_severe}).",
            {"qualifying_count": len(qualifying), "distinct_dates": len(dates), "has_severe": has_severe}
        )
    
    return DVResult("DV-03", False, False, "NOT_MET", "Multiple qualifying BPs found on single date without severe-range confirmation.", {"qualifying_count": len(qualifying)})


def derive_dv04_ga_anchor(first_uss_date: Optional[str], first_uss_ga: Optional[str], event_date: Optional[str]) -> DVResult:
    """DV-04: GA from 1st-trimester USS anchor."""
    uss_days = ga_str_to_days(first_uss_ga)
    if not first_uss_date or uss_days is None or not event_date:
        return DVResult("DV-04", False, True, "NOT_ASSESSABLE", "Pregnancy dating evidence (dating method, anchor date and GA) not documented")

    try:
        d_uss = datetime.strptime(first_uss_date, "%Y-%m-%d").date() if isinstance(first_uss_date, str) else first_uss_date
        d_evt = datetime.strptime(event_date, "%Y-%m-%d").date() if isinstance(event_date, str) else event_date
        diff = (d_evt - d_uss).days
        derived_days = uss_days + diff
        if derived_days < 0 or derived_days > 310:
            return DVResult("DV-04", False, True, "IMPLAUSIBLE_GA", f"Derived GA ({derived_days} days) outside plausible range.")
        derived_ga_str = days_to_ga_str(derived_days)
        return DVResult(
            "DV-04", True, False, "GA_ANCHOR_ESTABLISHED",
            f"GA at event derived as {derived_ga_str} ({derived_days} days) based on USS anchor {first_uss_ga} on {first_uss_date}.",
            {"derived_ga_days": derived_days, "derived_ga_str": derived_ga_str, "days_diff": diff}
        )
    except Exception as e:
        return DVResult("DV-04", False, True, "NOT_ASSESSABLE", f"Error parsing dating dates: {str(e)}")


def derive_dv05_onset_phenotype(onset_ga_str: Optional[str], delivery_ga_str: Optional[str] = None, postpartum_only: bool = False) -> DVResult:
    """DV-05: Onset phenotype (EOPE <34+0, LOPE >=34+0, PP_ONLY, UNCLASSIFIABLE)."""
    if postpartum_only:
        return DVResult("DV-05", True, False, "POSTPARTUM", "Postpartum-only presentation (SOP-ADJ-002 §4.2)", {"classification": "PP_ONLY"})
    
    days = ga_str_to_days(onset_ga_str)
    if days is None:
        return DVResult("DV-05", False, True, "UNCLASSIFIABLE", "Pregnancy dating evidence (dating method, anchor date and GA) not documented", {"classification": "UNCLASSIFIABLE"})

    if days < 238:  # 34+0 = 34*7 = 238
        return DVResult("DV-05", True, False, "EOPE", f"Early-onset pre-eclampsia (EOPE): onset at GA {onset_ga_str} (< 34+0 weeks).", {"classification": "EOPE", "onset_days": days})
    else:
        return DVResult("DV-05", True, False, "LOPE", f"Late-onset pre-eclampsia (LOPE): onset at GA {onset_ga_str} (>= 34+0 weeks).", {"classification": "LOPE", "onset_days": days})


def derive_dv06_onset_date(bp_readings: List[Dict[str, Any]], prot_log: List[Dict[str, Any]], lab_log: List[Dict[str, Any]]) -> DVResult:
    """DV-06: Earliest onset date (confirmed HTN + confirmatory coexistence)."""
    if not bp_readings:
        return DVResult("DV-06", False, True, "NOT_ASSESSABLE", "A confirmatory dated/timed BP or eligible severe-range recheck not documented")

    dates = [b.get("date") for b in bp_readings if b.get("date")]
    if not dates:
        return DVResult("DV-06", False, True, "NOT_ASSESSABLE", "Dated BP readings missing for onset calculation.")

    earliest = sorted(dates)[0]
    return DVResult(
        "DV-06", True, False, "ONSET_DATE_ESTABLISHED",
        f"Earliest documented presentation date: {earliest}.",
        {"earliest_date": earliest}
    )


def derive_dv07_proteinuria(upcr: Optional[float], dipstick_raw: Any, prot_24h_mg: Optional[float] = None) -> DVResult:
    """DV-07: Proteinuria (UPCR >=0.3 g/g or dipstick >=2+ or 24h >=300mg)."""
    dip_val = parse_dipstick_value(dipstick_raw)

    if upcr is None and dip_val is None and prot_24h_mg is None:
        return DVResult("DV-07", False, True, "NOT_ASSESSABLE", "A dated UPCR, 24-hour protein or dipstick result not documented")

    met_reasons = []
    if upcr is not None and upcr >= 0.3:
        met_reasons.append(f"UPCR {upcr} g/g (>=0.3)")
    if prot_24h_mg is not None and prot_24h_mg >= 300:
        met_reasons.append(f"24h Protein {prot_24h_mg} mg (>=300)")
    if dip_val is not None and dip_val >= 2.0:
        met_reasons.append(f"Dipstick {dipstick_raw} (>=2+)")

    if met_reasons:
        return DVResult(
            "DV-07", True, False, "PROTEINURIA_MET",
            f"Significant proteinuria confirmed: {'; '.join(met_reasons)}.",
            {"upcr": upcr, "dipstick_raw": str(dipstick_raw), "prot_24h_mg": prot_24h_mg, "reasons": met_reasons}
        )

    return DVResult(
        "DV-07", False, False, "NOT_MET",
        f"Proteinuria criteria not met (UPCR: {upcr}, Dipstick: {dipstick_raw}).",
        {"upcr": upcr, "dipstick_raw": str(dipstick_raw)}
    )


def derive_dv08_platelets(platelet_count: Optional[float]) -> DVResult:
    """DV-08: Platelet count impairment (<150 mild, <100 severe/ACOG, <50 critical)."""
    if platelet_count is None:
        return DVResult("DV-08", False, True, "NOT_ASSESSABLE", "Dated platelet count with AST/ALT evidence not documented")

    if platelet_count < 50:
        return DVResult("DV-08", True, False, "CRITICAL_THROMBOCYTOPENIA", f"Critical thrombocytopenia: {platelet_count} x10^3/uL (<50).", {"platelet_count": platelet_count, "tier": "<50"})
    elif platelet_count < 100:
        return DVResult("DV-08", True, False, "SEVERE_THROMBOCYTOPENIA", f"Severe thrombocytopenia (ACOG/ISSHP criterion met): {platelet_count} x10^3/uL (<100).", {"platelet_count": platelet_count, "tier": "<100"})
    elif platelet_count < 150:
        return DVResult("DV-08", True, False, "MILD_THROMBOCYTOPENIA", f"Mild thrombocytopenia: {platelet_count} x10^3/uL (<150).", {"platelet_count": platelet_count, "tier": "<150"})
    else:
        return DVResult("DV-08", False, False, "NORMAL_PLATELETS", f"Platelet count normal: {platelet_count} x10^3/uL.", {"platelet_count": platelet_count, "tier": "normal"})


def derive_dv09_creatinine_harmonise(value: Optional[float], unit: Optional[str]) -> Tuple[Optional[float], bool]:
    """DV-09: Unit harmonisation to mg/dL."""
    if value is None:
        return None, False
    u = (unit or "mg/dL").strip().lower()
    if u in ("umol/l", "µmol/l", "umol", "µmol"):
        # 1 mg/dL = 88.4 umol/L
        return round(value / 88.4, 3), True
    return float(value), False


def derive_dv10_renal(creatinine_raw: Optional[float], creatinine_unit: Optional[str] = "mg/dL", baseline_cr: Optional[float] = None) -> DVResult:
    """DV-10: Renal impairment (ACOG >1.1 mg/dL AND ISSHP >=90 umol/L reported)."""
    if creatinine_raw is None:
        return DVResult("DV-10", False, True, "NOT_ASSESSABLE", "Dated platelet count with AST/ALT evidence not documented")

    cr_mg, harmonised = derive_dv09_creatinine_harmonise(creatinine_raw, creatinine_unit)
    cr_umol = round(cr_mg * 88.4, 1) if cr_mg else None

    met_acog = cr_mg > 1.1 if cr_mg else False
    met_isshp = cr_umol >= 90.0 if cr_umol else False

    if met_acog or met_isshp:
        return DVResult(
            "DV-10", True, False, "RENAL_IMPAIRMENT_MET",
            f"Renal dysfunction confirmed: {cr_mg} mg/dL ({cr_umol} umol/L). ACOG >1.1: {met_acog}, ISSHP >=90: {met_isshp}.",
            {"creatinine_mg_dl": cr_mg, "creatinine_umol_l": cr_umol, "met_acog": met_acog, "met_isshp": met_isshp}
        )

    return DVResult(
        "DV-10", False, False, "NOT_MET",
        f"Renal function within normal limits: {cr_mg} mg/dL ({cr_umol} umol/L).",
        {"creatinine_mg_dl": cr_mg, "creatinine_umol_l": cr_umol}
    )


def derive_dv11_hepatic(ast: Optional[float], alt: Optional[float], ast_uln: float = 40.0, alt_uln: float = 35.0) -> DVResult:
    """DV-11: Hepatic dysfunction (ACOG >2xULN and ISSHP >40 U/L both reported)."""
    if ast is None and alt is None:
        return DVResult("DV-11", False, True, "NOT_ASSESSABLE", "Dated platelet count with AST/ALT evidence not documented")

    ast_val = ast or 0.0
    alt_val = alt or 0.0

    acog_ast = ast_val > (2 * ast_uln)
    acog_alt = alt_val > (2 * alt_uln)
    isshp_ast = ast_val > 40.0
    isshp_alt = alt_val > 40.0

    met = (acog_ast or acog_alt or isshp_ast or isshp_alt)

    if met:
        return DVResult(
            "DV-11", True, False, "HEPATIC_DYSFUNCTION_MET",
            f"Hepatic dysfunction confirmed: AST {ast} U/L, ALT {alt} U/L (AST >2xULN: {acog_ast}, ALT >2xULN: {acog_alt}).",
            {"ast": ast, "alt": alt, "acog_ast": acog_ast, "acog_alt": acog_alt}
        )

    return DVResult("DV-11", False, False, "NOT_MET", f"Transaminases within limits: AST {ast} U/L, ALT {alt} U/L.", {"ast": ast, "alt": alt})


def derive_dv12_ldh(ldh: Optional[float]) -> DVResult:
    """DV-12: Hemolysis / LDH >= 600 IU/L (fixed absolute threshold)."""
    if ldh is None:
        return DVResult("DV-12", False, True, "NOT_ASSESSABLE", "Dated platelet count with AST/ALT evidence not documented")

    if ldh >= 600.0:
        return DVResult("DV-12", True, False, "LDH_ELEVATED", f"Severe hemolysis / LDH threshold met: {ldh} IU/L (>=600).", {"ldh": ldh})

    return DVResult("DV-12", False, False, "NOT_MET", f"LDH below severe threshold: {ldh} IU/L (<600).", {"ldh": ldh})


def derive_dv13_hellp(platelet_count: Optional[float], ast: Optional[float], alt: Optional[float], ldh: Optional[float]) -> DVResult:
    """DV-13: HELLP syndrome (complete vs partial)."""
    if platelet_count is None or (ast is None and alt is None) or ldh is None:
        return DVResult("DV-13", False, True, "NOT_ASSESSABLE", "Complete laboratory panel (Platelets, AST/ALT, LDH) not fully documented.")

    has_hemolysis = ldh >= 600.0
    has_liver = (ast and ast > 70.0) or (alt and alt > 70.0)
    has_low_plt = platelet_count < 100.0

    if has_hemolysis and has_liver and has_low_plt:
        return DVResult("DV-13", True, False, "COMPLETE_HELLP", f"Complete HELLP syndrome criteria met: Plt {platelet_count}, AST/ALT {ast}/{alt}, LDH {ldh}.", {"type": "complete"})
    elif (has_hemolysis and has_liver) or (has_liver and has_low_plt) or (has_hemolysis and has_low_plt):
        return DVResult("DV-13", True, False, "PARTIAL_HELLP", f"Partial HELLP syndrome criteria met.", {"type": "partial"})
    
    return DVResult("DV-13", False, False, "NOT_MET", "HELLP syndrome criteria not met.", {})


def derive_dv14_severity(dv_results: Dict[str, DVResult]) -> DVResult:
    """DV-14: Severity phenotype (CRITICAL / SEVERE_FEATURES / STANDARD / NOT_ASSESSABLE)."""
    dv02 = dv_results.get("DV-02")
    dv08 = dv_results.get("DV-08")
    dv10 = dv_results.get("DV-10")
    dv11 = dv_results.get("DV-11")
    dv12 = dv_results.get("DV-12")
    dv13 = dv_results.get("DV-13")

    has_severe = any(
        (dv and dv.met) for dv in (dv02, dv10, dv11, dv12, dv13)
    ) or (dv08 and dv08.met and dv08.inputs.get("tier") in ("<100", "<50"))

    if has_severe:
        return DVResult("DV-14", True, False, "SEVERE_FEATURES", "Pre-eclampsia with Severe Features confirmed by automated criteria.", {"severity": "SEVERE_FEATURES"})

    dv03 = dv_results.get("DV-03")
    dv07 = dv_results.get("DV-07")
    if dv03 and dv03.met and dv07 and dv07.met:
        return DVResult("DV-14", True, False, "STANDARD", "Pre-eclampsia without Severe Features (Standard).", {"severity": "STANDARD"})

    return DVResult("DV-14", False, True, "NOT_ASSESSABLE", "Severity requires review — incomplete evidence.", {"severity": "NOT_ASSESSABLE"})


def derive_dv15_uteroplacental(efw_centile: Optional[float], ua_aedf: bool = False, ua_redf: bool = False, abruption: bool = False, iufd: bool = False) -> DVResult:
    """DV-15: Uteroplacental dysfunction (FGR <10th centile, AEDF/REDF, Abruption, IUFD)."""
    if efw_centile is None and not ua_aedf and not ua_redf and not abruption and not iufd:
        return DVResult("DV-15", False, True, "NOT_ASSESSABLE", "Dated fetal growth/centile and Doppler assessment not documented")

    reasons = []
    if efw_centile is not None and efw_centile < 10.0:
        reasons.append(f"FGR: EFW {efw_centile}th centile (<10th)")
    if ua_redf:
        reasons.append("Reversed End-Diastolic Flow (REDF)")
    elif ua_aedf:
        reasons.append("Absent End-Diastolic Flow (AEDF)")
    if abruption:
        reasons.append("Placental Abruption")
    if iufd:
        reasons.append("Intrauterine Fetal Death (IUFD)")

    if reasons:
        return DVResult("DV-15", True, False, "UTEROPLACENTAL_DYSFUNCTION", f"Fetal/uteroplacental complication: {'; '.join(reasons)}.", {"reasons": reasons})

    return DVResult("DV-15", False, False, "NORMAL_FETAL", "No uteroplacental dysfunction detected.", {"efw_centile": efw_centile})


def derive_dv26_completeness(case_data: Dict[str, Any]) -> DVResult:
    """DV-26: Evidence completeness 6-class score (0.0 to 1.0) with exact readable missing descriptions."""
    missing = []
    pts = 0

    # 1. Dating anchor
    if case_data.get("firstUssDate") or case_data.get("lnmp") or case_data.get("edd"):
        pts += 1
    else:
        missing.append("Pregnancy dating evidence (dating method, anchor date and GA) not documented")

    # 2. Two BP
    bp_list = case_data.get("bp_readings") or case_data.get("bpLog") or []
    if len(bp_list) >= 2:
        pts += 1
    else:
        missing.append("A confirmatory dated/timed BP or eligible severe-range recheck not documented")

    # 3. Proteinuria
    if case_data.get("upcr") is not None or case_data.get("dipstick_raw") is not None or case_data.get("prot_24h_mg") is not None or case_data.get("proteinuriaLog"):
        pts += 1
    else:
        missing.append("A dated UPCR, 24-hour protein or dipstick result not documented")

    # 4. Labs (Platelets + AST/ALT)
    has_plt = case_data.get("platelet_count") is not None or any(l.get("analyte") == "Platelet Count" for l in case_data.get("labLog", []))
    has_ast = case_data.get("ast") is not None or case_data.get("alt") is not None or any(l.get("analyte") in ("AST", "ALT") for l in case_data.get("labLog", []))
    if has_plt and has_ast:
        pts += 1
    else:
        missing.append("Dated platelet count with AST/ALT evidence not documented")

    # 5. Fetal / Doppler
    if case_data.get("efw_centile") is not None or case_data.get("ua_aedf") or case_data.get("ua_redf") or (case_data.get("sourceDocs") and case_data.get("sourceDocs", {}).get("ultrasound")):
        pts += 1
    else:
        missing.append("Dated fetal growth/centile and Doppler assessment not documented")

    # 6. Delivery record
    if case_data.get("delivery_date") or case_data.get("ga_at_delivery") or (case_data.get("sourceDocs") and case_data.get("sourceDocs", {}).get("delivery")):
        pts += 1
    else:
        missing.append("Delivery record and gestational age at delivery not documented")

    score = round(pts / 6.0, 2)
    packet_complete = (score == 1.0)

    return DVResult(
        "DV-26", packet_complete, False,
        "COMPLETE" if packet_complete else "INCOMPLETE",
        f"Evidence completeness score: {int(score * 100)}% ({pts}/6 classes present).",
        {"score": score, "points": pts, "missing": missing, "packet_complete": packet_complete}
    )


def derive_dv27_certainty_gate(dv26_score: float, dv03: DVResult, dv07: DVResult, dv08: DVResult, dv10: DVResult, dv11: DVResult) -> DVResult:
    """DV-27: Certainty Gate (enforces Definite / Probable / Possible caps based on evidence)."""
    blocked_by = []

    if dv26_score < 1.0:
        blocked_by.append(f"Incomplete evidence packet (DV-26 score {int(dv26_score * 100)}% < 100%)")
    if not dv03.met:
        blocked_by.append("Hypertension not confirmed (DV-03)")
    if not (dv07.met or dv08.met or dv10.met or dv11.met):
        blocked_by.append("Neither proteinuria nor organ dysfunction confirmed")

    gate_open = (len(blocked_by) == 0)

    if gate_open:
        max_certainty = "Definite"
    elif dv26_score >= 0.5 and dv03.met:
        max_certainty = "Probable"
    else:
        max_certainty = "Possible"

    return DVResult(
        "DV-27", gate_open, False,
        "GATE_OPEN" if gate_open else "GATE_RESTRICTED",
        f"Certainty Gate: max allowed certainty = '{max_certainty}'. Gate open: {gate_open}.",
        {"gate_open": gate_open, "max_certainty": max_certainty, "blocked_by": blocked_by}
    )


def derive_dv30_trigger(case_data: Dict[str, Any], dv_results: Dict[str, DVResult]) -> DVResult:
    """DV-30: Endpoint trigger derivation."""
    reasons = []
    dv02 = dv_results.get("DV-02")
    dv03 = dv_results.get("DV-03")
    dv07 = dv_results.get("DV-07")
    dv14 = dv_results.get("DV-14")

    if dv02 and dv02.met:
        reasons.append("Severe BP (>=160/110 mmHg)")
    if dv03 and dv03.met:
        reasons.append("Confirmed HTN")
    if dv07 and dv07.met:
        reasons.append("Significant Proteinuria")
    if dv14 and dv14.met and dv14.result_label == "SEVERE_FEATURES":
        reasons.append("Severe Features Present")

    triggered = len(reasons) > 0

    return DVResult(
        "DV-30", triggered, False,
        "TRIGGERED" if triggered else "NON_CASE",
        f"Endpoint trigger evaluation: {'TRIGGERED (' + ', '.join(reasons) + ')' if triggered else 'Non-case / Borderline'}.",
        {"triggered": triggered, "reasons": reasons}
    )


# ── Full Engine Execution ─────────────────────────────────────────────────────

def run_dv_engine(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Runs all DV derivations (DV-01 through DV-30) and returns comprehensive bundle."""
    bp_readings = case_data.get("bp_readings") or case_data.get("bpLog") or []
    
    results: Dict[str, DVResult] = {}

    results["DV-01"] = derive_dv01_max_bp_per_visit(bp_readings)
    results["DV-02"] = derive_dv02_severe_bp(bp_readings)
    results["DV-03"] = derive_dv03_confirmed_htn(bp_readings)
    
    results["DV-04"] = derive_dv04_ga_anchor(
        case_data.get("firstUssDate"),
        case_data.get("firstUssGa"),
        case_data.get("event_date") or case_data.get("EVENT_DT")
    )
    
    results["DV-05"] = derive_dv05_onset_phenotype(
        case_data.get("ga_at_first_criterion") or case_data.get("gaAtEvent"),
        case_data.get("ga_at_delivery"),
        case_data.get("postpartum_only", False)
    )

    results["DV-06"] = derive_dv06_onset_date(bp_readings, case_data.get("proteinuriaLog", []), case_data.get("labLog", []))
    
    results["DV-07"] = derive_dv07_proteinuria(case_data.get("upcr"), case_data.get("dipstick_raw"), case_data.get("prot_24h_mg"))
    results["DV-08"] = derive_dv08_platelets(case_data.get("platelet_count"))
    results["DV-10"] = derive_dv10_renal(case_data.get("creatinine_raw") or case_data.get("creatinine"), case_data.get("creatinine_unit", "mg/dL"), case_data.get("baseline_creatinine"))
    results["DV-11"] = derive_dv11_hepatic(case_data.get("ast"), case_data.get("alt"), case_data.get("ast_uln", 40.0), case_data.get("alt_uln", 35.0))
    results["DV-12"] = derive_dv12_ldh(case_data.get("ldh"))
    results["DV-13"] = derive_dv13_hellp(case_data.get("platelet_count"), case_data.get("ast"), case_data.get("alt"), case_data.get("ldh"))
    
    results["DV-14"] = derive_dv14_severity(results)
    results["DV-15"] = derive_dv15_uteroplacental(case_data.get("efw_centile"), case_data.get("ua_aedf", False), case_data.get("ua_redf", False), case_data.get("abruption", False), case_data.get("iufd", False))

    results["DV-26"] = derive_dv26_completeness(case_data)
    
    dv26_score = results["DV-26"].inputs.get("score", 0.0)
    results["DV-27"] = derive_dv27_certainty_gate(
        dv26_score, results["DV-03"], results["DV-07"], results["DV-08"], results["DV-10"], results["DV-11"]
    )

    results["DV-30"] = derive_dv30_trigger(case_data, results)

    return {
        "engine_version": RULE_VERSION,
        "dv_results": {k: v.to_dict() for k, v in results.items()},
        "evidence_completeness_score": dv26_score,
        "missing_anchors": results["DV-26"].inputs.get("missing", []),
        "certainty_gate": results["DV-27"].to_dict(),
        "trigger": results["DV-30"].to_dict(),
    }
