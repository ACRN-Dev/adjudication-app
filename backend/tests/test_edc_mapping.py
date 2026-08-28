from services.edc_mapping import is_edc_schema, normalize_edc_rows
from services.realtime_mapping import map_variable


def test_edc_wide_schema_normalizes_into_canonical_long_rows():
    headers=["SUBJID","EVENT","EVENT_DT","GA_EVENT","SBP","DBP","PLT"]
    assert is_edc_schema(headers)
    rows=list(normalize_edc_rows([{"SUBJID":"P-001","EVENT":"Visit 2","EVENT_DT":"2026-08-01","GA_EVENT":"33","SBP":"160","DBP":"110","PLT":"92"}]))
    assert {map_variable(r) for r in rows} >= {"VISIT_DATE","GA_WEEKS","SBP","DBP","PLATELETS"}
    assert all(r["MRN"] == "P-001" and r["Form Title"] == "Visit 2" for r in rows)


def test_edc_missing_visit_keys_are_retained_for_monitor_qc():
    rows=list(normalize_edc_rows([{"SUBJID":"P-002","SBP":"150","DBP":"100"}]))
    assert rows
    assert rows[0]["_EDC_MISSING_VISIT_KEY"] is True
    assert "EXCLUDED VISIT" in rows[0]["Form Title"]


def test_edc_row_without_subject_is_safely_excluded():
    assert list(normalize_edc_rows([{"SUBJID":"","EVENT":"Visit 1","SBP":"140"}])) == []
