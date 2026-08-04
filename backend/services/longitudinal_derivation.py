"""Visit and cumulative longitudinal derivations with no future evidence leakage."""
from datetime import timedelta
from models.longitudinal import VisitDerivation, LongitudinalCaseDerivation
from services.dv_engine import run_dv_engine

def _case_from_observations(observations):
    data={"bp_readings":[],"proteinuriaLog":[],"labLog":[]}
    by={}
    for o in observations:
        by.setdefault(o.canonical_variable,[]).append(o)
        v=o.numeric_value if o.numeric_value is not None else o.coded_value or o.parsed_text_value
        if o.canonical_variable in {"SBP","SBP_RECHECK","DBP","DBP_RECHECK"}: continue
        key={"PLATELETS":"platelet_count","CREATININE":"creatinine","AST":"ast","ALT":"alt","LDH":"ldh","UPCR":"upcr","DIPSTICK_PROTEIN":"dipstick_raw","EFW_CENTILE":"efw_centile","DELIVERY_DATE":"delivery_date"}.get(o.canonical_variable)
        if key in {"platelet_count","creatinine","ast","alt","ldh","upcr","efw_centile"}:
            if o.numeric_value is not None: data[key]=o.numeric_value
        elif key=="delivery_date":
            if o.datetime_value: data[key]=o.datetime_value
        elif key: data[key]=v
    # Preserve every BP row. Pair only values that share visit and source row neighbourhood.
    sbps=by.get("SBP",[]); dbps=by.get("DBP",[])
    for i,o in enumerate(sbps):
        sbp=o.numeric_value; dbp=dbps[i].numeric_value if i<len(dbps) else None
        if sbp is None and dbp is None: continue
        data["bp_readings"].append({"sbp":sbp or 0,"dbp":dbp or 0,"datetime":o.observation_datetime})
    if by.get("DATING_ANCHOR_DATE"): data["firstUssDate"]=by["DATING_ANCHOR_DATE"][0].datetime_value
    if by.get("DATING_ANCHOR_GA"): data["firstUssGa"]=by["DATING_ANCHOR_GA"][0].parsed_text_value
    return data

def derive_participant(db, participant, visits):
    cumulative=[]; first=None; earliest_htn=None; earliest_confirmation=None; max_severity="NOT_ASSESSABLE"; latest_bundle=None
    for visit in sorted(visits,key=lambda v:(v.visit_datetime is None,v.visit_datetime or v.visit_sequence,v.visit_sequence)):
        eligible=[o for o in visit.observations if not o.prohibited_flag and o.provenance_type!="MOCK_SUPPLEMENT"]
        cumulative.extend(eligible)
        bundle=run_dv_engine(_case_from_observations(cumulative)); latest_bundle=bundle
        for dv_id,result in bundle["dv_results"].items():
            db.add(VisitDerivation(participant_id=participant.id,visit_id=visit.id,dv_identifier=dv_id,result=result,status=result.get("result_label"),inputs=result.get("inputs",{}),missing_inputs=result.get("inputs",{}).get("missing",[])))
        d3=bundle["dv_results"].get("DV-03",{}); d7=bundle["dv_results"].get("DV-07",{}); organ=any(bundle["dv_results"].get(x,{}).get("met") for x in ("DV-08","DV-10","DV-11","DV-12","DV-15"))
        if d3.get("met") and earliest_htn is None: earliest_htn=visit.visit_datetime
        if (d7.get("met") or organ) and earliest_confirmation is None: earliest_confirmation=visit.visit_datetime
        if first is None and d3.get("met") and (d7.get("met") or organ) and visit.visit_datetime: first=visit
        if bundle["dv_results"].get("DV-14",{}).get("result_label") in {"SEVERE_FEATURES","CRITICAL"}: max_severity=bundle["dv_results"]["DV-14"]["result_label"]
    onset=first.visit_datetime if first else None; ga=first.gestational_age_days if first else None
    classification="UNCLASSIFIABLE"
    if onset and ga is not None: classification="EOPE" if ga<238 else "LOPE"
    recorded=[o for v in visits for o in v.observations if o.canonical_variable=="RECORDED_PE_DIAGNOSIS"]
    recorded_date=[o for v in visits for o in v.observations if o.canonical_variable=="RECORDED_PE_DIAGNOSIS_DATE"]
    deriv=LongitudinalCaseDerivation(participant_id=participant.id,earliest_hypertension_date=earliest_htn,earliest_bp_confirmation_date=earliest_htn,earliest_qualifying_confirmation_date=earliest_confirmation,earliest_qualifying_pe_date=onset,first_qualifying_visit_id=first.id if first else None,gestational_age_at_onset_days=ga,onset_classification=classification,maximum_severity=max_severity,packet_completeness=(latest_bundle or {}).get("evidence_completeness_score",0),certainty_restriction=(latest_bundle or {}).get("certainty_gate",{}).get("inputs",{}).get("max_certainty","Possible"),trigger_status=(latest_bundle or {}).get("trigger",{}).get("result_label","NON_CASE"),recorded_site_diagnosis=(recorded[-1].parsed_text_value if recorded else None),recorded_site_diagnosis_date=(recorded_date[-1].datetime_value if recorded_date else None),recorded_versus_derived_discrepancy={"different":bool(recorded and not first)},explanation=(f"The system identifies {first.scheduled_visit_code} as the earliest visit containing dated hypertension and qualifying confirmation." if first else "No visit contains sufficient dated evidence for a supportable PE onset."))
    db.add(deriv)
    participant.first_qualifying_visit_id=deriv.first_qualifying_visit_id; participant.derived_onset_date=onset; participant.derived_onset_classification=classification
    participant.maximum_severity=max_severity; participant.packet_completeness=deriv.packet_completeness
    return deriv
