"""Visit and cumulative longitudinal derivations with no future evidence leakage."""
from datetime import datetime, timedelta
from models.longitudinal import VisitDerivation, LongitudinalCaseDerivation
from services.clinical_derivation import RULE_VERSION, derive_clinical_bundle

CANONICAL_ALIASES = {
    "visit_date": "VISIT_DATE", "ega_weeks": "GA_WEEKS", "ega_days": "GA_DAYS",
    "dating_anchor_date": "DATING_ANCHOR_DATE", "dating_anchor_ga": "DATING_ANCHOR_GA",
    "bp_systolic": "SBP", "bp_diastolic": "DBP", "bp_systolic_recheck": "SBP_RECHECK", "bp_diastolic_recheck": "DBP_RECHECK",
    "platelets": "PLATELETS", "creatinine": "CREATININE", "ast": "AST", "alt": "ALT", "ldh": "LDH",
    "upcr": "UPCR", "ua_protein": "DIPSTICK_PROTEIN", "efw": "EFW_CENTILE", "delivery_date": "DELIVERY_DATE",
}


def _canonical_name(value):
    """Normalize mapper output and legacy uppercase names to one contract."""
    raw = str(value or "").strip()
    return CANONICAL_ALIASES.get(raw.lower(), raw.upper())


def _observation_sort_key(observation):
    event_datetime = observation.observation_datetime or observation.datetime_value
    return (
        event_datetime is None,
        event_datetime or datetime.min,
        observation.source_row_number is None,
        observation.source_row_number or 0,
        str(getattr(observation, "id", "")),
    )


def _bp_group_key(observation, canonical):
    """Group only measurements that can safely belong to the same BP event.

    Base and recheck fields are separate series.  Visit, form, page and event
    time must all agree before a systolic and diastolic value may be paired.
    """
    series = "RECHECK" if canonical.endswith("_RECHECK") else "BASE"
    return (
        str(observation.visit_id),
        observation.source_form or "",
        observation.source_page or "",
        observation.observation_datetime or observation.datetime_value,
        series,
    )


def _pair_bp_group(sbps, dbps):
    """Return deterministic, unambiguous SBP/DBP pairs for one source event."""
    if len(sbps) == 1 and len(dbps) == 1:
        return [(sbps[0], dbps[0])], []

    unmatched_dbps = list(dbps)
    pairs = []
    unmatched = []
    for sbp in sbps:
        if sbp.source_row_number is None:
            unmatched.append(sbp)
            continue
        distances = [
            (abs(sbp.source_row_number - dbp.source_row_number), dbp)
            for dbp in unmatched_dbps
            if dbp.source_row_number is not None
        ]
        if not distances:
            unmatched.append(sbp)
            continue
        minimum = min(distance for distance, _ in distances)
        nearest = [dbp for distance, dbp in distances if distance == minimum]
        # A source-row gap of one is the only unambiguous repeated-measurement
        # relationship available in the current RealTime export contract.
        if minimum != 1 or len(nearest) != 1:
            unmatched.append(sbp)
            continue
        dbp = nearest[0]
        unmatched_dbps.remove(dbp)
        pairs.append((sbp, dbp))
    unmatched.extend(unmatched_dbps)
    return pairs, unmatched


def _case_from_observations(observations):
    data={"bp_readings":[],"proteinuriaLog":[],"labLog":[],"unpaired_bp_observations":[]}
    by={}
    for o in sorted(observations, key=_observation_sort_key):
        canonical = _canonical_name(o.canonical_variable)
        by.setdefault(canonical,[]).append(o)
        v=o.numeric_value if o.numeric_value is not None else o.coded_value or o.parsed_text_value
        if canonical in {"SBP","SBP_RECHECK","DBP","DBP_RECHECK"}: continue
        key={"PLATELETS":"platelet_count","CREATININE":"creatinine","AST":"ast","ALT":"alt","LDH":"ldh","UPCR":"upcr","DIPSTICK_PROTEIN":"dipstick_raw","EFW_CENTILE":"efw_centile","DELIVERY_DATE":"delivery_date"}.get(canonical)
        if key in {"platelet_count","creatinine","ast","alt","ldh","upcr","efw_centile"}:
            if o.numeric_value is not None: data[key]=o.numeric_value
        elif key=="delivery_date":
            if o.datetime_value: data[key]=o.datetime_value
        elif key: data[key]=v
    bp_groups={}
    for canonical in ("SBP", "DBP", "SBP_RECHECK", "DBP_RECHECK"):
        side = "sbp" if canonical.startswith("SBP") else "dbp"
        for observation in by.get(canonical, []):
            group = bp_groups.setdefault(_bp_group_key(observation, canonical), {"sbp": [], "dbp": []})
            group[side].append(observation)
    for group_key, group in bp_groups.items():
        pairs, unmatched = _pair_bp_group(group["sbp"], group["dbp"])
        for sbp_observation, dbp_observation in pairs:
            event_datetime = sbp_observation.observation_datetime or sbp_observation.datetime_value
            data["bp_readings"].append({
                "sbp": sbp_observation.numeric_value,
                "dbp": dbp_observation.numeric_value,
                "datetime": event_datetime,
                "date": event_datetime.date().isoformat() if event_datetime else None,
                "source": sbp_observation.source_form or "RealTime",
                "source_rows": [sbp_observation.source_row_number, dbp_observation.source_row_number],
                "series": group_key[-1],
            })
        data["unpaired_bp_observations"].extend([
            {
                "canonical_variable": _canonical_name(observation.canonical_variable),
                "source_row": observation.source_row_number,
                "source_form": observation.source_form,
                "source_page": observation.source_page,
            }
            for observation in unmatched
        ])
    if by.get("DATING_ANCHOR_DATE"): data["firstUssDate"]=by["DATING_ANCHOR_DATE"][0].datetime_value
    if by.get("DATING_ANCHOR_GA"): data["firstUssGa"]=by["DATING_ANCHOR_GA"][0].parsed_text_value
    return data

def derive_participant(db, participant, visits):
    cumulative=[]; first=None; earliest_htn=None; earliest_confirmation=None; max_severity="NOT_ASSESSABLE"; latest_bundle=None
    for visit in sorted(visits,key=lambda v:(v.visit_datetime is None,v.visit_datetime or v.visit_sequence,v.visit_sequence)):
        eligible=[o for o in visit.observations if not o.prohibited_flag and not o.superseded and o.provenance_type!="MOCK_SUPPLEMENT"]
        cumulative.extend(eligible)
        bundle=derive_clinical_bundle(_case_from_observations(cumulative)); latest_bundle=bundle
        for dv_id,result in bundle["dv_results"].items():
            persisted = db.query(VisitDerivation).filter_by(visit_id=visit.id, dv_identifier=dv_id).first()
            if persisted is None:
                persisted = VisitDerivation(participant_id=participant.id, visit_id=visit.id, dv_identifier=dv_id)
                db.add(persisted)
            persisted.result = result
            persisted.status = result.get("result_label")
            persisted.inputs = result.get("inputs", {})
            persisted.missing_inputs = result.get("inputs", {}).get("missing", [])
            persisted.rule_version = RULE_VERSION
            persisted.derived_at = datetime.utcnow()
        d3=bundle["dv_results"].get("DV-03",{}); d7=bundle["dv_results"].get("DV-07",{}); organ=any(bundle["dv_results"].get(x,{}).get("met") for x in ("DV-08","DV-10","DV-11","DV-12","DV-15"))
        if d3.get("met") and earliest_htn is None: earliest_htn=visit.visit_datetime
        if (d7.get("met") or organ) and earliest_confirmation is None: earliest_confirmation=visit.visit_datetime
        if first is None and d3.get("met") and (d7.get("met") or organ) and visit.visit_datetime: first=visit
        if bundle["dv_results"].get("DV-14",{}).get("result_label") in {"SEVERE_FEATURES","CRITICAL"}: max_severity=bundle["dv_results"]["DV-14"]["result_label"]
    onset=first.visit_datetime if first else None; ga=first.gestational_age_days if first else None
    classification="UNCLASSIFIABLE"
    if onset and ga is not None: classification="EOPE" if ga<238 else "LOPE"
    recorded=[o for v in visits for o in v.observations if not o.superseded and o.canonical_variable=="RECORDED_PE_DIAGNOSIS"]
    recorded_date=[o for v in visits for o in v.observations if not o.superseded and o.canonical_variable=="RECORDED_PE_DIAGNOSIS_DATE"]
    deriv = db.query(LongitudinalCaseDerivation).filter_by(participant_id=participant.id).first()
    if deriv is None:
        deriv = LongitudinalCaseDerivation(participant_id=participant.id)
        db.add(deriv)
    deriv.earliest_hypertension_date=earliest_htn; deriv.earliest_bp_confirmation_date=earliest_htn
    deriv.earliest_qualifying_confirmation_date=earliest_confirmation; deriv.earliest_qualifying_pe_date=onset
    deriv.first_qualifying_visit_id=first.id if first else None; deriv.gestational_age_at_onset_days=ga
    deriv.onset_classification=classification; deriv.maximum_severity=max_severity
    deriv.packet_completeness=(latest_bundle or {}).get("evidence_completeness_score",0)
    deriv.certainty_restriction=(latest_bundle or {}).get("certainty_gate",{}).get("inputs",{}).get("max_certainty","Possible")
    deriv.trigger_status=(latest_bundle or {}).get("trigger",{}).get("result_label","NON_CASE")
    deriv.recorded_site_diagnosis=(recorded[-1].parsed_text_value if recorded else None)
    deriv.recorded_site_diagnosis_date=(recorded_date[-1].datetime_value if recorded_date else None)
    deriv.recorded_versus_derived_discrepancy={"different":bool(recorded and not first)}
    deriv.explanation=(f"The system identifies {first.scheduled_visit_code} as the earliest visit containing dated hypertension and qualifying confirmation." if first else "No visit contains sufficient dated evidence for a supportable PE onset.")
    deriv.derivation_version=RULE_VERSION; deriv.derived_at=datetime.utcnow()
    participant.first_qualifying_visit_id=deriv.first_qualifying_visit_id; participant.derived_onset_date=onset; participant.derived_onset_classification=classification
    participant.maximum_severity=max_severity; participant.packet_completeness=deriv.packet_completeness
    return deriv
