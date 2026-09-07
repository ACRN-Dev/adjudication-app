"""
ACRN PROTECT-Africa / LOPE-Nigeria Endpoint Adjudication Platform
Visit 5 Fetal and Neonatal Assessment Domain Service

Remaps Visit 5 into structured, closed-ended fetal and neonatal assessment fields
tied to study team source data with strict provenance, precedence, and mutual exclusivity.
"""

from typing import List, Dict, Any, Optional, Tuple
import re

# Standard closed-ended assessment codes and human-readable labels
ASSESSMENT_CODES = {
    "PERINATAL_FETAL_DEATH": "Perinatal / fetal death",
    "DELIVERY_GE_37W": "Delivery at or after 37 weeks",
    "DELIVERY_LT_34W": "Delivery before 34 weeks",
    "IUGR": "IUGR",
    "SGA": "SGA",
    "NORMAL_OUTCOME": "Normal fetal / neonatal outcome, where clinically approved",
}

ADVERSE_ASSESSMENT_CODES = {
    "PERINATAL_FETAL_DEATH",
    "DELIVERY_LT_34W",
    "IUGR",
    "SGA",
}

PREGNANCY_OUTCOME_PRECEDENCE = [
    "Stillbirth",
    "Early neonatal death",
    "Preterm birth",
    "Congenital abnormalities",
    "Normal baby",
    "Completed",
    "Ongoing",
]


def normalize_val(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()


def is_affirmative(val: Any) -> bool:
    v = normalize_val(val).lower()
    return v in ("yes", "y", "true", "1", "# - yes", "confirmed", "positive")


def is_negative(val: Any) -> bool:
    v = normalize_val(val).lower()
    return v in ("no", "n", "false", "0", "# - no", "none", "not confirmed", "negative")


def is_blank_or_zero(val: Any) -> bool:
    v = normalize_val(val)
    return not v or v in ("0", "none", "null", "not answered", "unspecified")


def parse_numeric_ga(val: Any) -> Optional[float]:
    if val is None:
        return None
    v_str = str(val).replace(",", ".").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", v_str)
    if m:
        try:
            num = float(m.group(1))
            if 15.0 <= num <= 45.0:
                return num
        except ValueError:
            return None
    return None


def extract_visit5_source_evidence(observations: List[Any]) -> Dict[str, Any]:
    """
    Extracts relevant Visit 5 fields from raw canonical observations or dicts.
    Returns structured observations keyed by clinical concept with provenance.
    """
    evidence: Dict[str, List[Dict[str, Any]]] = {
        "ga_delivery": [],
        "delivery_lt_34w": [],
        "pregnancy_outcome": [],
        "delivery_type": [],
        "delivery_assessment_done": [],
        "iugr_sga_assessment_done": [],
        "confirmed_iugr": [],
        "confirmed_sga": [],
        "efw": [],
        "afi": [],
        "pathologic_flow": [],
        "newborn_assessment_done": [],
        "newborn_ga": [],
        "birth_weight": [],
        "newborn_physical_exam": [],
        "birth_complications": [],
        "congenital_anomalies": [],
        "nicu_admission": [],
        "apgar_1min": [],
        "apgar_5min": [],
        "newborn_disorder_assessment_done": [],
        "newborn_abnormal_finding": [],
    }

    for obs in observations:
        # Support both SQLAlchemy model objects and dictionary dicts
        label = normalize_val(getattr(obs, "source_field_label", None) or (obs.get("source_field_label") if isinstance(obs, dict) else "") or (obs.get("field") if isinstance(obs, dict) else ""))
        form = normalize_val(getattr(obs, "source_form", None) or (obs.get("source_form") if isinstance(obs, dict) else "") or (obs.get("form") if isinstance(obs, dict) else ""))
        raw_val = getattr(obs, "raw_source_value", None) or (obs.get("raw_source_value") if isinstance(obs, dict) else "") or (obs.get("value") if isinstance(obs, dict) else "")
        obs_dt = getattr(obs, "observation_datetime", None) or (obs.get("observation_datetime") if isinstance(obs, dict) else "") or (obs.get("observed_at") if isinstance(obs, dict) else "")
        canonical = getattr(obs, "canonical_variable", None) or (obs.get("canonical_variable") if isinstance(obs, dict) else "")

        item = {
            "form": form,
            "field": label,
            "raw_value": raw_val,
            "canonical": canonical,
            "observed_at": str(obs_dt) if obs_dt else None,
        }

        lbl_lower = label.lower()
        form_lower = form.lower()

        # 1. Gestational age at delivery
        if "gestational age at delivery" in lbl_lower or canonical == "GA_AT_DELIVERY":
            evidence["ga_delivery"].append(item)
        elif "gestational age" in lbl_lower and "newborn" in form_lower:
            evidence["newborn_ga"].append(item)

        # 2. Delivery < 34 weeks
        if "delivery <34 weeks" in lbl_lower or "delivery < 34 weeks" in lbl_lower or canonical == "DELIVERY_LT_34W":
            evidence["delivery_lt_34w"].append(item)

        # 3. Pregnancy outcome
        if "pregnancy outcome" in lbl_lower or canonical == "PREGNANCY_OUTCOME":
            evidence["pregnancy_outcome"].append(item)

        # 4. Delivery type
        if "type of delivery" in lbl_lower:
            evidence["delivery_type"].append(item)

        # 5. Delivery assessment performed
        if "was the delivery outcome status assessment performed" in lbl_lower:
            evidence["delivery_assessment_done"].append(item)

        # 6. IUGR and SGA assessment performed
        if "were iugr and sga assessments done" in lbl_lower or "iugr and sga assessment" in lbl_lower:
            evidence["iugr_sga_assessment_done"].append(item)

        # 7. Confirmed IUGR
        if "confirmed iugr" in lbl_lower or (lbl_lower == "iugr" and "iugr" in form_lower) or canonical == "CONFIRMED_IUGR":
            evidence["confirmed_iugr"].append(item)

        # 8. Confirmed SGA
        if "confirmed sga" in lbl_lower or (lbl_lower == "sga" and "sga" in form_lower) or canonical == "CONFIRMED_SGA":
            evidence["confirmed_sga"].append(item)

        # 9. Pathologic flow & AFI
        if "pathologic flow" in lbl_lower or canonical in ("AEDF", "REDF"):
            evidence["pathologic_flow"].append(item)
        if "amniotic fluid index" in lbl_lower or canonical == "AFI":
            evidence["afi"].append(item)
        if "estimated fetal weight" in lbl_lower or canonical == "EFW":
            evidence["efw"].append(item)

        # 10. Newborn assessment
        if "birth weight" in lbl_lower:
            evidence["birth_weight"].append(item)
        if "physical examination" in lbl_lower and "newborn" in form_lower:
            evidence["newborn_physical_exam"].append(item)
        if "birth complications" in lbl_lower:
            evidence["birth_complications"].append(item)
        if "congenital anomalies" in lbl_lower:
            evidence["congenital_anomalies"].append(item)
        if "neonatal icu admission" in lbl_lower or "icu admission" in lbl_lower:
            evidence["nicu_admission"].append(item)
        if "apgar score at 1 minute" in lbl_lower:
            evidence["apgar_1min"].append(item)
        if "apgar score at 5 minutes" in lbl_lower:
            evidence["apgar_5min"].append(item)

        # 11. Newborn disorders
        if "was the newborn disorder status assessment performed" in lbl_lower:
            evidence["newborn_disorder_assessment_done"].append(item)
        if "was there any abnormal finding" in lbl_lower:
            evidence["newborn_abnormal_finding"].append(item)

    return evidence


def map_source_to_visit5_assessments(observations: List[Any]) -> Dict[str, Any]:
    """
    Deterministically maps raw Visit 5 source observations into candidate closed-ended
    assessments and supporting fields, preserving full provenance and distinguishing
    missing data from confirmed negatives.
    """
    ev = extract_visit5_source_evidence(observations)

    # ── Supporting Field 1: Gestational Age at Delivery ────────────────────────
    ga_val: Optional[float] = None
    ga_provenance: Optional[Dict[str, Any]] = None

    for item in ev["ga_delivery"] + ev["newborn_ga"]:
        parsed = parse_numeric_ga(item["raw_value"])
        if parsed is not None:
            ga_val = parsed
            ga_provenance = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": item["raw_value"],
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            break

    # ── Supporting Field 2: Pregnancy Outcome (Precedence Applied) ───────────
    pregnancy_outcome_val: Optional[str] = None
    outcome_provenance: Optional[Dict[str, Any]] = None

    # Sort collected values according to precedence
    candidates: List[Tuple[int, Dict[str, Any], str]] = []
    for item in ev["pregnancy_outcome"]:
        raw = normalize_val(item["raw_value"])
        if raw and raw not in ("0", "none"):
            # Check match in precedence
            prec_idx = 999
            matched_name = raw
            for idx, p_name in enumerate(PREGNANCY_OUTCOME_PRECEDENCE):
                if p_name.lower() in raw.lower():
                    prec_idx = idx
                    matched_name = p_name
                    break
            candidates.append((prec_idx, item, matched_name))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        best = candidates[0]
        pregnancy_outcome_val = best[2]
        outcome_provenance = {
            "source_form": best[1]["form"],
            "source_field": best[1]["field"],
            "raw_value": best[1]["raw_value"],
            "observed_at": best[1]["observed_at"],
            "confidence": "EXACT",
        }

    # ── Map the 6 Closed-Ended Assessment States ──────────────────────────────
    assessments_map: Dict[str, Dict[str, Any]] = {}

    # 1. Perinatal / fetal death
    death_state = "NOT_ASSESSED_OR_MISSING"
    death_prov = None
    if pregnancy_outcome_val in ("Stillbirth", "Early neonatal death"):
        death_state = "CONFIRMED_POSITIVE"
        death_prov = outcome_provenance
    elif pregnancy_outcome_val in ("Normal baby", "Preterm birth"):
        death_state = "CONFIRMED_NEGATIVE"
        death_prov = outcome_provenance
    assessments_map["PERINATAL_FETAL_DEATH"] = {
        "code": "PERINATAL_FETAL_DEATH",
        "label": ASSESSMENT_CODES["PERINATAL_FETAL_DEATH"],
        "state": death_state,
        "is_suggested": death_state == "CONFIRMED_POSITIVE",
        "provenance": death_prov,
    }

    # 2. Delivery at or after 37 weeks
    ge_37_state = "NOT_ASSESSED_OR_MISSING"
    ge_37_prov = None
    if ga_val is not None:
        if ga_val >= 37.0:
            ge_37_state = "CONFIRMED_POSITIVE"
            ge_37_prov = ga_provenance
        else:
            ge_37_state = "CONFIRMED_NEGATIVE"
            ge_37_prov = ga_provenance
    assessments_map["DELIVERY_GE_37W"] = {
        "code": "DELIVERY_GE_37W",
        "label": ASSESSMENT_CODES["DELIVERY_GE_37W"],
        "state": ge_37_state,
        "is_suggested": ge_37_state == "CONFIRMED_POSITIVE",
        "provenance": ge_37_prov,
    }

    # 3. Delivery before 34 weeks
    lt_34_state = "NOT_ASSESSED_OR_MISSING"
    lt_34_prov = None
    # Check explicit field first
    has_explicit_lt_34 = False
    for item in ev["delivery_lt_34w"]:
        if is_affirmative(item["raw_value"]):
            lt_34_state = "CONFIRMED_POSITIVE"
            lt_34_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": item["raw_value"],
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            has_explicit_lt_34 = True
            break
        elif is_negative(item["raw_value"]):
            lt_34_state = "CONFIRMED_NEGATIVE"
            lt_34_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": item["raw_value"],
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            has_explicit_lt_34 = True
            break

    if not has_explicit_lt_34 and ga_val is not None:
        if ga_val < 34.0:
            lt_34_state = "CONFIRMED_POSITIVE"
            lt_34_prov = ga_provenance
        else:
            lt_34_state = "CONFIRMED_NEGATIVE"
            lt_34_prov = ga_provenance

    assessments_map["DELIVERY_LT_34W"] = {
        "code": "DELIVERY_LT_34W",
        "label": ASSESSMENT_CODES["DELIVERY_LT_34W"],
        "state": lt_34_state,
        "is_suggested": lt_34_state == "CONFIRMED_POSITIVE",
        "provenance": lt_34_prov,
    }

    # 4. IUGR (Intrauterine Growth Restriction)
    iugr_state = "NOT_ASSESSED_OR_MISSING"
    iugr_prov = None
    iugr_assessment_done = False
    for item in ev["iugr_sga_assessment_done"]:
        if is_affirmative(item["raw_value"]):
            iugr_assessment_done = True
            break

    for item in ev["confirmed_iugr"]:
        raw = item["raw_value"]
        if is_affirmative(raw):
            iugr_state = "CONFIRMED_POSITIVE"
            iugr_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": raw,
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            break
        elif is_negative(raw) or "# - no" in str(raw).lower():
            iugr_state = "CONFIRMED_NEGATIVE"
            iugr_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": raw,
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            break

    if iugr_state == "NOT_ASSESSED_OR_MISSING" and iugr_assessment_done:
        # Check pathological flow
        for item in ev["pathologic_flow"]:
            if is_affirmative(item["raw_value"]):
                iugr_state = "CONFIRMED_POSITIVE"
                iugr_prov = {
                    "source_form": item["form"],
                    "source_field": item["field"],
                    "raw_value": item["raw_value"],
                    "observed_at": item["observed_at"],
                    "confidence": "INFERRED",
                }
                break

    assessments_map["IUGR"] = {
        "code": "IUGR",
        "label": ASSESSMENT_CODES["IUGR"],
        "state": iugr_state,
        "is_suggested": iugr_state == "CONFIRMED_POSITIVE",
        "provenance": iugr_prov,
    }

    # 5. SGA (Small for Gestational Age)
    sga_state = "NOT_ASSESSED_OR_MISSING"
    sga_prov = None
    for item in ev["confirmed_sga"]:
        raw = item["raw_value"]
        if is_affirmative(raw):
            sga_state = "CONFIRMED_POSITIVE"
            sga_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": raw,
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            break
        elif is_negative(raw) or "# - no" in str(raw).lower():
            sga_state = "CONFIRMED_NEGATIVE"
            sga_prov = {
                "source_form": item["form"],
                "source_field": item["field"],
                "raw_value": raw,
                "observed_at": item["observed_at"],
                "confidence": "EXACT",
            }
            break

    assessments_map["SGA"] = {
        "code": "SGA",
        "label": ASSESSMENT_CODES["SGA"],
        "state": sga_state,
        "is_suggested": sga_state == "CONFIRMED_POSITIVE",
        "provenance": sga_prov,
    }

    # 6. Normal fetal / neonatal outcome, where clinically approved
    normal_state = "NOT_ASSESSED_OR_MISSING"
    normal_prov = None
    has_any_adverse = any(
        assessments_map[k]["state"] == "CONFIRMED_POSITIVE"
        for k in ADVERSE_ASSESSMENT_CODES
    )
    if not has_any_adverse:
        # Check if term delivery and normal baby
        is_term = ge_37_state == "CONFIRMED_POSITIVE"
        is_normal_baby = pregnancy_outcome_val == "Normal baby"

        # Check newborn exam complications
        has_newborn_complication = any(
            is_affirmative(item["raw_value"])
            for item in ev["birth_complications"] + ev["congenital_anomalies"] + ev["nicu_admission"]
        )

        if is_term and is_normal_baby and not has_newborn_complication:
            normal_state = "CONFIRMED_POSITIVE"
            normal_prov = {
                "summary": "Term delivery (>=37w), normal newborn assessment, absence of adverse outcomes",
                "ga_delivery": ga_val,
                "pregnancy_outcome": pregnancy_outcome_val,
                "confidence": "CLINICALLY_PROPOSED",
            }
        elif has_any_adverse:
            normal_state = "CONFIRMED_NEGATIVE"
    else:
        normal_state = "CONFIRMED_NEGATIVE"

    assessments_map["NORMAL_OUTCOME"] = {
        "code": "NORMAL_OUTCOME",
        "label": ASSESSMENT_CODES["NORMAL_OUTCOME"],
        "state": normal_state,
        "is_suggested": normal_state == "CONFIRMED_POSITIVE",
        "provenance": normal_prov,
    }

    suggested_list = [k for k, v in assessments_map.items() if v["is_suggested"]]

    return {
        "gestational_age_at_delivery": ga_val,
        "gestational_age_provenance": ga_provenance,
        "pregnancy_outcome": pregnancy_outcome_val,
        "pregnancy_outcome_provenance": outcome_provenance,
        "assessments": assessments_map,
        "suggested_assessments": suggested_list,
    }


def validate_visit5_submission(
    assessments: List[str],
    ga_at_delivery: Optional[float] = None,
    pregnancy_outcome: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validates Visit 5 closed-ended assessments against precedence and mutual exclusivity rules.
    Returns (is_valid, error_message).
    """
    selected_set = set(assessments or [])

    # Validate known codes
    invalid_codes = selected_set - set(ASSESSMENT_CODES.keys())
    if invalid_codes:
        return False, f"Unrecognized assessment code(s): {', '.join(invalid_codes)}"

    # 1. Normal vs Adverse mutual exclusivity
    if "NORMAL_OUTCOME" in selected_set:
        adverse_present = selected_set.intersection(ADVERSE_ASSESSMENT_CODES)
        if adverse_present:
            adverse_labels = [ASSESSMENT_CODES[c] for c in adverse_present]
            return False, (
                f"Normal fetal / neonatal outcome cannot coexist with adverse outcome(s): {', '.join(adverse_labels)}. "
                "Please deselect Normal outcome or the adverse outcome."
            )

    # 2. Gestational age delivery mutual exclusivity (>= 37w vs < 34w)
    if "DELIVERY_GE_37W" in selected_set and "DELIVERY_LT_34W" in selected_set:
        return False, (
            "A delivery cannot be both 'Delivery at or after 37 weeks' and 'Delivery before 34 weeks'. "
            "These gestational age delivery outcomes are mutually exclusive."
        )

    # 3. Numeric GA consistency check
    if ga_at_delivery is not None:
        if "DELIVERY_GE_37W" in selected_set and ga_at_delivery < 37.0:
            return False, (
                f"Gestational age at delivery ({ga_at_delivery} weeks) contradicts 'Delivery at or after 37 weeks'. "
                "Ensure gestational age matches the selected delivery category."
            )
        if "DELIVERY_LT_34W" in selected_set and ga_at_delivery >= 34.0:
            return False, (
                f"Gestational age at delivery ({ga_at_delivery} weeks) contradicts 'Delivery before 34 weeks'. "
                "Ensure gestational age matches the selected delivery category."
            )

    # 4. Perinatal / fetal death consistency
    if "PERINATAL_FETAL_DEATH" in selected_set:
        if pregnancy_outcome and pregnancy_outcome.lower() == "normal baby":
            return False, (
                "Perinatal / fetal death cannot be selected when pregnancy outcome is 'Normal baby'. "
                "Pregnancy outcome precedence requires death documentation (Stillbirth / Early neonatal death)."
            )

    return True, None


def compare_visit5_concordance(
    assessments_a: Optional[List[str]],
    assessments_b: Optional[List[str]],
    ga_a: Optional[float] = None,
    ga_b: Optional[float] = None,
) -> bool:
    """
    Evaluates whether Reviewer A and Reviewer B agree on Visit 5 determinations.
    """
    set_a = set(assessments_a or [])
    set_b = set(assessments_b or [])
    if set_a != set_b:
        return False

    # If both provided GA, allow tolerance of 0.5 weeks (e.g. 37 vs 37.2)
    if ga_a is not None and ga_b is not None:
        if abs(ga_a - ga_b) > 0.5:
            return False

    return True
