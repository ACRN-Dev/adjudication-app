from types import SimpleNamespace
from models.canonical import ReviewerRole
from services.adjudication_resolution import resolve_visit


def rec(role, diagnosis="PE", severity="WITH_SEVERE", certainty="DEFINITE", date="2026-08-01"):
    return SimpleNamespace(reviewer_role=role,signed=True,meets_criteria=True,diagnosis=diagnosis,
        onset_class="EOPE",severity=severity,certainty=certainty,date_of_diagnosis=date)


def test_a_b_full_determination_concordance_adopts_a():
    a=rec(ReviewerRole.REVIEWER_A); b=rec(ReviewerRole.REVIEWER_B)
    status, adopted, reason=resolve_visit(None,[a,b])
    assert (status,adopted,reason)==("CONCORDANT",a,"A_B_CONCORDANT")


def test_severity_difference_requires_reviewer_c():
    a=rec(ReviewerRole.REVIEWER_A); b=rec(ReviewerRole.REVIEWER_B,severity="WITHOUT_SEVERE")
    assert resolve_visit(None,[a,b])[0]=="AWAITING_REVIEWER_C"


def test_majority_adopts_matching_record_not_automatically_c():
    a=rec(ReviewerRole.REVIEWER_A); b=rec(ReviewerRole.REVIEWER_B,severity="WITHOUT_SEVERE"); c=rec(ReviewerRole.REVIEWER_C)
    status,adopted,reason=resolve_visit(None,[a,b,c])
    assert status=="RESOLVED_BY_MAJORITY" and adopted is a and reason=="C_WITH_A"
