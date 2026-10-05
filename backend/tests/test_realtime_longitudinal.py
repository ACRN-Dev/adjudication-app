"""Synthetic RealTime-shaped privacy, mapping, reconstruction and temporal tests."""
from services.realtime_mapping import classify,map_variable,parse_datetime,parse_numeric,parse_coded,visit_code
from services.realtime_pipeline import pseudonym,_fernet
from services.import_readiness import participant_import_readiness
from api.realtime import _timeline_visit_number

def row(label,page="Vital Signs / Weight Height",form="Visit 3",value="",field_type="numeric",export=""):
    return {"MRN":"TEST-MRN","Screening #":"ZWE999-0001","Randomization #":"R-TEST","Form Title":form,"Form Version":"1.0","Page Title":page,"Field type":field_type,"Field Label":label,"Data Input":value,"Data Value":value,"Audit Trails":"Synthetic User - 01/Jan/2026","Export Variable Name":export}

def test_composite_mapping_without_export_variable_name():
    assert map_variable(row("Systolic blood pressure"))=="bp_systolic"
    assert map_variable(row("Diastolic blood pressure recheck"))=="bp_diastolic_recheck"
    assert map_variable(row("Creatinine",page="Biochemistry Results"))=="creatinine"

def test_rt_map_20_excludes_direct_identifiers():
    assert classify(row("Date of Birth", page="Demographics")) == "DIRECT_IDENTIFIER"

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


def test_timeline_signature_status_uses_scheduled_visit_number():
    visit = type("Visit", (), {"scheduled_visit_code": "Visit 04"})()
    assert _timeline_visit_number(visit, 2) == 4

def test_controlled_parsers_preserve_missing_semantics():
    assert parse_numeric("168 mmHg")==168
    assert parse_coded("Flag: Not Done")=="NOT_DONE"
    assert parse_datetime("05/28/2026 08:20:03") is not None

def test_source_datetime_parser_supports_real_time_date_variants():
    assert parse_datetime("22/Apr/2026 10:57:00 SAST").isoformat() == "2026-04-22T10:57:00"
    assert parse_datetime("22/04/2026 10:57").isoformat() == "2026-04-22T10:57:00"
    assert parse_datetime("2026-04-22T10:57:00Z").isoformat() == "2026-04-22T10:57:00"


def test_collection_indicators_are_not_mapped_as_lab_results():
    assert map_variable(row("Was a urine protein dipstick test performed?", page="Assessment of Proteinuria")) is None
    assert map_variable(row("Was a spot urine test for protein/creatinine ratio performed?", page="Assessment of Proteinuria")) is None
    assert classify(row("Was a urine protein dipstick test performed?", page="Assessment of Proteinuria")) == "CLINICAL_COLLECTION_STATUS"


def test_source_interpretation_is_context_not_result_value():
    r = row("Red blood cell count result interpretation", page="Hematology")
    assert map_variable(r) == "source_interpretation_rbc"
    assert classify(r) == "CLINICAL_RESULT_INTERPRETATION"


def test_readiness_accepts_evidence_rich_visit_with_missing_date_as_warning():
    obs = type("Obs", (), {"prohibited_flag": False, "canonical_variable": "bp_systolic"})()
    visit = type("Visit", (), {
        "scheduled_visit_code": "V01",
        "visit_datetime": None,
        "observations": [obs],
        "qc_status": "PENDING",
        "visit_occurrence": 1,
    })()
    participant = type("Participant", (), {"visits": [visit]})()
    readiness = participant_import_readiness(participant)
    assert readiness["status"] == "ACCEPTED_WITH_WARNINGS"
    assert readiness["accepted"] is True
    assert "Visit date is missing" in readiness["warnings"][0]


def test_readiness_duplicate_scheduled_visit_keeps_more_complete_instance():
    sparse = type("Visit", (), {
        "scheduled_visit_code": "V02",
        "visit_datetime": None,
        "observations": [],
        "qc_status": "PENDING",
        "visit_occurrence": 2,
    })()
    complete = type("Visit", (), {
        "scheduled_visit_code": "V02",
        "visit_datetime": parse_datetime("22/04/2026 10:57"),
        "observations": [type("Obs", (), {"prohibited_flag": False, "canonical_variable": "bp_systolic"})()],
        "qc_status": "PENDING",
        "visit_occurrence": 1,
    })()
    participant = type("Participant", (), {"visits": [sparse, complete]})()
    readiness = participant_import_readiness(participant)
    v02 = next(item for item in readiness["visits"] if item["visit"] == "V02")
    assert v02["status"] == "ACCEPTED_WITH_WARNINGS"
    assert v02["mapped_fields"] == 1
