from datetime import datetime, timedelta

from services.derivation_engine import derive_hep_02, derive_htn_01
from services.dv_engine import (
    derive_dv03_confirmed_htn,
    derive_dv10_renal,
    derive_dv11_hepatic,
    derive_dv12_ldh,
    derive_dv14_severity,
)


START = datetime(2026, 7, 1, 8, 0)


def bp_pair(interval):
    return [
        {"sbp": 145, "dbp": 92, "datetime": START},
        {"sbp": 146, "dbp": 94, "datetime": START + interval},
    ]


def test_both_engines_accept_exact_six_hour_boundary():
    readings = bp_pair(timedelta(hours=6))
    assert derive_htn_01(readings).met is True
    assert derive_dv03_confirmed_htn(readings).met is True


def test_both_engines_reject_below_six_hours():
    readings = bp_pair(timedelta(hours=5, minutes=59))
    assert derive_htn_01(readings).met is False
    assert derive_dv03_confirmed_htn(readings).met is False


def test_both_engines_reject_more_than_one_week():
    readings = bp_pair(timedelta(days=7, seconds=1))
    assert derive_htn_01(readings).met is False
    assert derive_dv03_confirmed_htn(readings).met is False


def test_date_only_values_do_not_bypass_timestamp_requirement():
    readings = [
        {"sbp": 165, "dbp": 112, "date": "2026-07-01"},
        {"sbp": 166, "dbp": 114, "date": "2026-07-02"},
    ]
    primary = derive_htn_01(readings)
    dv = derive_dv03_confirmed_htn(readings)
    assert primary.met is False
    assert primary.missingness_status == "NOT_DOCUMENTED"
    assert dv.met is False
    assert dv.not_assessable is True


def test_ldh_must_exceed_600_in_both_engines():
    assert derive_hep_02(600).met is False
    assert derive_dv12_ldh(600).met is False
    assert derive_hep_02(601).met is True
    assert derive_dv12_ldh(601).met is True


def test_renal_criterion_uses_baseline_doubling_and_oliguria():
    doubled = derive_dv10_renal(0.8, baseline_cr=0.4)
    oliguria = derive_dv10_renal(None, oliguria=True)
    normal = derive_dv10_renal(0.8, baseline_cr=0.7)
    assert doubled.met is True
    assert doubled.inputs["doubled_baseline"] is True
    assert oliguria.met is True
    assert normal.met is False


def test_missing_lab_messages_are_criterion_specific():
    assert "creatinine" in derive_dv10_renal(None).details.lower()
    assert "ast or alt" in derive_dv11_hepatic(None, None).details.lower()
    assert "ldh" in derive_dv12_ldh(None).details.lower()


def test_severity_wording_requires_adjudicator_confirmation():
    severe = type("Result", (), {"met": True, "inputs": {}})()
    result = derive_dv14_severity({"DV-02": severe})
    assert result.met is True
    assert "adjudicator confirmation is required" in result.details.lower()
    assert "confirmed by automated" not in result.details.lower()
