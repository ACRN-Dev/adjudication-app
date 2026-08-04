import os,sys,pytest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from services.clinical_import_policy import is_recorded_pe_outcome,classify_realtime_field,assert_not_adjudicator_outcome_mapping,evidence_only_payload

@pytest.mark.parametrize("label",["Preeclampsia Status","PE_STATUS","Recorded PE diagnosis","PE Diagnosis Date","Final Diagnosis"])
def test_recorded_pe_fields_are_restricted(label): assert is_recorded_pe_outcome(label)
def test_realtime_recorded_diagnosis_classified_restricted(): assert classify_realtime_field(field_label="Was pre-eclampsia diagnosed?")=="RESTRICTED_RECORDED_OUTCOME"
@pytest.mark.parametrize("source,canonical",[("PE_STATUS","clinical_status"),("site field","RECORDED_PE_DIAGNOSIS"),("Final diagnosis","diagnosis")])
def test_outcome_mapping_to_adjudicator_rejected(source,canonical):
    with pytest.raises(HTTPException): assert_not_adjudicator_outcome_mapping(source,canonical)
def test_outcome_fields_removed_before_derivation():
    source={"SBP":162,"DBP":108,"PE_STATUS":"Yes","RECORDED_PE_DIAGNOSIS":"Severe PE"}
    clean=evidence_only_payload(source)
    assert clean=={"SBP":162,"DBP":108}
def test_clinical_evidence_remains_available(): assert not is_recorded_pe_outcome("Systolic blood pressure")
