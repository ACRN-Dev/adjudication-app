import pytest
from services.history_parser import (
    compute_risk_summary,
    finalize_history,
    history_domain,
    make_field_key,
    parse_partial_date,
    parse_php_serialized_instances,
    sanitize_audit_trail,
)
from models.history import PatientHistoryField

def test_parse_php_serialized_instances():
    # Empty cases
    assert parse_php_serialized_instances(None) == {None: None}
    assert parse_php_serialized_instances("0") == {None: None}
    assert parse_php_serialized_instances("") == {None: None}
    
    # Plain text without instance prefix
    assert parse_php_serialized_instances("Hypertension") == {None: "Hypertension"}
    
    # Simple single instance
    assert parse_php_serialized_instances('#1 - s:12:"Hypertension";') == {1: "Hypertension"}
    
    # Empty instance value
    assert parse_php_serialized_instances('#1 - N;') == {1: None}
    assert parse_php_serialized_instances('#1 - N') == {1: None}
    
    # Multiple instances
    text = '#1 - s:12:"Hypertension"; #2 - s:7:"ongoing"; #3 - N;'
    res = parse_php_serialized_instances(text)
    assert res == {1: "Hypertension", 2: "ongoing", 3: None}
    
    # Date string with space
    assert parse_php_serialized_instances('#1 - s:19:"6/16/2026 00:00:00 ";') == {1: "6/16/2026 00:00:00 "}

def test_history_label_whitespace_collapses_for_keys():
    assert make_field_key("Did the participant  have IUGR  in a previous  pregnancy?") == "did_the_participant_have_iugr_in_a_previous_pregnancy"

def test_realtime_history_page_routing_uses_three_adjudicator_domains():
    assert history_domain("Screening |V01", "Obstetric history") == "obstetric"
    assert history_domain("Screening |V01", "Medical History") == "conditions"
    assert history_domain("Screening |V01", "Family History") == "conditions"
    assert history_domain("Screening |V01", "Allergies / Surgeries") == "conditions"
    assert history_domain("Medical History / Prior & Concomitant Medications + Sync", "Medical Conditions") == "conditions"
    assert history_domain("Medical History / Prior & Concomitant Medications + Sync", "Medications / Treatments") == "medications"

def test_parse_partial_date():
    assert parse_partial_date("0") == (None, None)
    assert parse_partial_date("0/0/2014") == ("2014", "year-only")
    assert parse_partial_date("6/0/2026") == ("06/2026", "month-year")
    assert parse_partial_date("6/15/2026 00:00:00") == ("6/15/2026", "full")

def test_sanitize_audit_trail():
    dt, ahash = sanitize_audit_trail("Makaha, Edward - 04/Mar/2026 01:20:21 PM CAT")
    # Date should parse correctly (but may fail on CAT timezone if unsupported by strptime, so we might need a fallback test)
    # Note: strptime %Z is notoriously finicky. Let's see if our sanitize_audit_trail handles exceptions:
    assert ahash is not None
    # No staff names should be in the hash
    assert "Makaha" not in str(ahash)
    assert "Edward" not in str(ahash)
    assert dt is not None

def test_compute_risk_summary():
    fields = [
        PatientHistoryField(field_key="does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies", value="Yes"),
        PatientHistoryField(field_key="medical_condition", value="Hypertension, Chronic", domain="medical"),
        PatientHistoryField(field_key="number_of_live_births", value="2"),
        PatientHistoryField(field_key="number_of_still_births", value="1"),
    ]
    summary = compute_risk_summary(fields)
    assert "Prior Severe PE" in summary["chips"]
    assert "Pre-existing chronic HTN" in summary["chips"]
    assert summary["parity"] == 2
    assert summary["stillbirths"] == 1
    assert "P2" in summary["parity_summary"]
    assert "+1SB" in summary["parity_summary"]

def test_not_known_remains_distinct_value():
    field = PatientHistoryField(field_key="family_history_known", value="Not known", domain="conditions")
    assert field.value == "Not known"

def test_make_field_key_page_disambiguation():
    # Medical conditions primary page retains standard keys
    assert make_field_key("End Date", "Medical Conditions") == "end_date"
    assert make_field_key("Start Date", "Medical Conditions") == "start_date"
    assert make_field_key("Medical Condition", "Medical Conditions") == "medical_condition"
    
    # Other condition pages with repeating end_date/start_date are disambiguated
    assert make_field_key("End Date", "Allergies") == "allergies_end_date"
    assert make_field_key("End Date", "Surgeries, Procedures and Hospitalizations") == "surgeries_procedures_and_hospitalizations_end_date"
    assert make_field_key("Start Date", "Surgeries, Procedures and Hospitalizations") == "surgeries_procedures_and_hospitalizations_start_date"
    assert make_field_key("Electronic Signature Lock Date/Time", "Obstetric history") == "obstetric_history_electronic_signature_lock_date_time"
    assert make_field_key("Electronic Signature Lock Date/Time", "Medical History") == "medical_history_electronic_signature_lock_date_time"

def test_process_history_row_in_session_deduplication():
    from conftest import TestingSession
    from models.history import PatientHistoryField, PatientHistory
    from models.longitudinal import RTImportBatch, LongitudinalParticipant
    import uuid
    from services.history_parser import process_history_row
    
    db = TestingSession()
    
    batch = RTImportBatch(id=uuid.uuid4(), filename="test.csv", checksum="dummy-checksum-123", file_size=100, uploaded_by="tester", status="PROCESSING")
    p = LongitudinalParticipant(id=uuid.uuid4(), blinded_subject_id="ACRN-TEST-01", study="PROTECT-Africa", source_batch_id=batch.id)
    db.add(batch)
    db.add(p)
    db.flush()
    
    # First occurrence: allergy question with 'Yes'
    row1 = {
        "Form Title": "Medical History / Prior & Concomitant Medications + Sync",
        "Page Title": "Allergies",
        "Field Label": "Does the subject have any allergies or intolerances to report?",
        "Field type": "yes_no",
        "Data Value": "Yes",
        "Audit Trails": "Makaha, Edward - 04/Mar/2026 01:20:21 PM CAT"
    }
    history_fields = {}
    patient_histories = {}
    process_history_row(db, batch, p, row1, 1, history_fields=history_fields, patient_histories=patient_histories)
    
    # Second occurrence in same session without commit (simulating RealTime duplicate row with empty update):
    row2 = {
        "Form Title": "Medical History / Prior & Concomitant Medications + Sync",
        "Page Title": "Allergies",
        "Field Label": "Does the subject have any allergies or intolerances to report?",
        "Field type": "yes_no",
        "Data Value": "",
        "Audit Trails": ""
    }
    process_history_row(db, batch, p, row2, 2, history_fields=history_fields, patient_histories=patient_histories)
    
    # Commit must not raise sqlite3.IntegrityError
    db.commit()
    
    # Must only have 1 PatientHistoryField record, and value must be preserved as 'Yes'
    fields = db.query(PatientHistoryField).filter_by(participant_id=p.id).all()
    assert len(fields) == 1
    assert fields[0].value == "Yes"
    
    db.close()

