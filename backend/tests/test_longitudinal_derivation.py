from datetime import datetime
from types import SimpleNamespace

from services.longitudinal_derivation import _case_from_observations


EVENT_TIME = datetime(2026, 6, 1, 8, 0)


def observation(variable, value=None, row=1, page="Vitals", form="Visit", event_time=EVENT_TIME):
    return SimpleNamespace(
        id=f"{variable}-{row}",
        visit_id="visit-1",
        canonical_variable=variable,
        numeric_value=value,
        coded_value=None,
        parsed_text_value=None,
        datetime_value=None,
        observation_datetime=event_time,
        source_form=form,
        source_page=page,
        source_row_number=row,
    )


def test_lowercase_mapper_names_populate_case_values():
    case = _case_from_observations([
        observation("platelets", 91, row=10),
        observation("creatinine", 1.2, row=11),
        observation("upcr", 0.4, row=12),
    ])

    assert case["platelet_count"] == 91
    assert case["creatinine"] == 1.2
    assert case["upcr"] == 0.4


def test_base_and_recheck_bp_values_pair_within_their_own_series():
    case = _case_from_observations([
        observation("bp_diastolic_recheck", 112, row=14),
        observation("bp_systolic", 150, row=11),
        observation("bp_diastolic", 95, row=12),
        observation("bp_systolic_recheck", 165, row=13),
    ])

    assert [(reading["sbp"], reading["dbp"], reading["series"]) for reading in case["bp_readings"]] == [
        (150, 95, "BASE"),
        (165, 112, "RECHECK"),
    ]
    assert all(reading["date"] == "2026-06-01" for reading in case["bp_readings"])
    assert case["unpaired_bp_observations"] == []


def test_repeated_measurements_pair_only_adjacent_source_rows():
    case = _case_from_observations([
        observation("bp_systolic", 140, row=21),
        observation("bp_diastolic", 90, row=22),
        observation("bp_systolic", 160, row=31),
        observation("bp_diastolic", 110, row=32),
    ])

    assert [(reading["sbp"], reading["dbp"]) for reading in case["bp_readings"]] == [
        (140, 90),
        (160, 110),
    ]


def test_bp_values_from_different_source_pages_are_not_cross_paired():
    case = _case_from_observations([
        observation("bp_systolic", 170, row=10, page="Triage"),
        observation("bp_diastolic", 115, row=11, page="Ward"),
    ])

    assert case["bp_readings"] == []
    assert len(case["unpaired_bp_observations"]) == 2
