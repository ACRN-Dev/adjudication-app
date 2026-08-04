"""Synthetic RealTime-shaped privacy, mapping, reconstruction and temporal tests."""
from services.realtime_mapping import classify,map_variable,parse_datetime,parse_numeric,parse_coded,visit_code
from services.realtime_pipeline import pseudonym,_fernet

def row(label,page="Vital Signs / Weight Height",form="Visit 3",value="",field_type="numeric",export=""):
    return {"MRN":"TEST-MRN","Screening #":"ZWE999-0001","Randomization #":"R-TEST","Form Title":form,"Form Version":"1.0","Page Title":page,"Field type":field_type,"Field Label":label,"Data Input":value,"Data Value":value,"Audit Trails":"Synthetic User - 01/Jan/2026","Export Variable Name":export}

def test_composite_mapping_without_export_variable_name():
    assert map_variable(row("Systolic blood pressure"))=="SBP"
    assert map_variable(row("Diastolic blood pressure recheck"))=="DBP_RECHECK"
    assert map_variable(row("Creatinine",page="Biochemistry Results"))=="CREATININE"

def test_biomarkers_are_rejected_before_canonical_ingestion():
    for label in ("Tigsun PlGF/sFLT-1","Biomarker result","sEng normal range","POC result"):
        assert classify(row(label,page="Biomarker Analysis"))=="PROHIBITED_BLINDED"

def test_identifiers_and_staff_metadata_are_not_clinical_evidence():
    assert classify(row("PTID",page="Lab Sample Collection Form"))=="DIRECT_IDENTIFIER"
    assert classify(row("Research Nurse (Actual)",page="Lab Sample Collection Form"))=="RESTRICTED_OPERATIONAL_METADATA"
    assert classify(row("Electronic Signature Lock Date/Time"))=="RESTRICTED_OPERATIONAL_METADATA"

def test_recorded_diagnosis_is_comparison_metadata():
    r=row("Preeclampsia diagnosis description",page="Maternal Preeclampsia Assessment")
    assert map_variable(r)=="RECORDED_PE_DIAGNOSIS"
    assert classify(r)=="RESTRICTED_RECORDED_OUTCOME"

def test_pseudonym_is_stable_and_does_not_embed_mrn():
    a=pseudonym("6959","ZWE001-0030"); b=pseudonym("6959","ZWE001-0030")
    assert a==b and a.startswith("ACRN-") and "6959" not in a and "0030" not in a

def test_crosswalk_ciphertext_is_not_plaintext_and_is_recoverable():
    token=_fernet.encrypt(b"6959")
    assert b"6959" not in token and _fernet.decrypt(token)==b"6959"

def test_scheduled_unscheduled_and_event_visits_remain_separate():
    assert visit_code("Screening |V01")==("V01",1,"SCHEDULED")
    assert visit_code("Visit 6 - EOS")==("V06",6,"SCHEDULED")
    assert visit_code("Unscheduled visit |01")[2]=="UNSCHEDULED"
    assert visit_code("Adverse Event |01")[2]=="EVENT"

def test_controlled_parsers_preserve_missing_semantics():
    assert parse_numeric("168 mmHg")==168
    assert parse_coded("Flag: Not Done")=="NOT_DONE"
    assert parse_datetime("05/28/2026 08:20:03") is not None
