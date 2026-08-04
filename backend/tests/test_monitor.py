import os,sys,pytest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from services.monitor_security import scan_blinding,validate_import,qc_gate,assignment_gate,release_gate
from services.workflow_policy import check_reviewer_isolation,check_committee_quorum,evaluate_concordance
def test_prohibited_fields_quarantined(): assert scan_blinding(['export_PlGF.csv'])['state']=='UNBLINDING_QUARANTINE'
def test_clean_blinded_file_passes(): assert scan_blinding(['edc_bp.csv'])['passed']
def test_duplicate_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','same',['participant_id'],[{'participant_id':'1'}],{'same'})
def test_empty_import_rejected():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['participant_id'],[],set())
def test_required_header_enforced():
    with pytest.raises(HTTPException): validate_import('x.csv','new',['bp'],[{'bp':120}],set())
def test_mandatory_pre_qc_blocks_release():
    with pytest.raises(HTTPException): qc_gate([{'mandatory':True,'response':'Fail'}])
def test_pre_qc_passes(): qc_gate([{'mandatory':True,'response':'Pass'},{'mandatory':False,'response':'N/A'}])
def test_same_reviewer_cannot_fill_both_roles():
    with pytest.raises(HTTPException): assignment_gate('a','a',{'a'})
def test_ineligible_reviewer_rejected():
    with pytest.raises(HTTPException): assignment_gate('a','b',{'a'})
def test_reviewer_isolation_preserved(): assert check_reviewer_isolation('A','B','QA_RELEASED') is False
def test_concordance_and_discordance():
    a={'primary_diagnosis':'PE','onset_classification':'EOPE','severity_phenotype':'severe','certainty_level':'definite'}
    assert evaluate_concordance(a,a)['concordant']; b={**a,'certainty_level':'probable'}; assert not evaluate_concordance(a,b)['concordant']
def test_committee_quorum_gate(): assert not check_committee_quorum(2).allowed and check_committee_quorum(3).allowed
def test_final_qc_gate():
    with pytest.raises(HTTPException): release_gate('Fail',True)
    with pytest.raises(HTTPException): release_gate('Pass',False)
    release_gate('Pass',True)

