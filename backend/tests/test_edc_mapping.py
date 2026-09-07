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


def test_clinical_one_schema_detection():
    from services.edc_mapping import is_clinical_one_schema
    headers = [
        "Study Version", "Site", "Subject ID", "Screening Number", "Subject Number",
        "Date & Time", "Visit/Event Title", "Visit/Event Instance", "Form Title",
        "Repeating Section Number", "Question Label", "Type of Change", "Value",
        "Unit of Measure", "Lab ID-Lab Name", "Reason for Change", "User Name"
    ]
    assert is_clinical_one_schema(headers) is True
    assert is_edc_schema(headers) is True


def test_clinical_one_rows_normalization_and_lab_collation():
    from services.edc_mapping import normalize_clinical_one_rows
    c1_rows = [
        # Lab form with repeating sections
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 1 (Screening)", "Form Title": "CLINICAL CHEMISTRY",
            "Repeating Section Number": "3", "Question Label": "Lab Test", "Value": "Creatinine",
            "Date & Time": "01-May-2026 13:14", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 1 (Screening)", "Form Title": "CLINICAL CHEMISTRY",
            "Repeating Section Number": "3", "Question Label": "Lab Result", "Value": "76",
            "Date & Time": "01-May-2026 13:14", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 1 (Screening)", "Form Title": "CLINICAL CHEMISTRY",
            "Repeating Section Number": "3", "Question Label": "Lab Unit", "Value": "mmol/L",
            "Date & Time": "01-May-2026 13:14", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Vital signs form
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 3", "Form Title": "VITAL SIGNS",
            "Repeating Section Number": "N/A", "Question Label": "Systolic", "Value": "145",
            "Unit of Measure": "mmHg", "Date & Time": "01-May-2026 13:18", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 3", "Form Title": "VITAL SIGNS",
            "Repeating Section Number": "N/A", "Question Label": "Diastolic", "Value": "92",
            "Unit of Measure": "mmHg", "Date & Time": "01-May-2026 13:18", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Visit 5 Delivery form
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 5 - Delivery", "Form Title": "DELIVERY OUTCOME",
            "Repeating Section Number": "N/A", "Question Label": "Weeks", "Value": "38",
            "Date & Time": "09-Jun-2026 10:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 5 - Delivery", "Form Title": "DELIVERY OUTCOME",
            "Repeating Section Number": "N/A", "Question Label": "Days", "Value": "3",
            "Date & Time": "09-Jun-2026 10:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 5 - Delivery", "Form Title": "DELIVERY OUTCOME",
            "Repeating Section Number": "N/A", "Question Label": "Pregnancy Outcome", "Value": "Normal baby",
            "Date & Time": "09-Jun-2026 10:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Newborn Assessment
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 5 - Delivery", "Form Title": "NEWBORN ASSESSMENT (DELIVERY)",
            "Repeating Section Number": "N/A", "Question Label": "Confirmed IUGR?", "Value": "No",
            "Date & Time": "09-Jun-2026 10:30", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
    ]

    normalized = list(normalize_clinical_one_rows(c1_rows))
    assert len(normalized) >= 5

    # Check collated lab observation
    creat = next((r for r in normalized if r["Field Label"] == "Creatinine"), None)
    assert creat is not None
    assert creat["Data Value"] == "76"
    assert "mmol/L" in creat["Data Input"]
    assert map_variable(creat) == "CREATININE"

    # Check vital signs
    sbp = next((r for r in normalized if r["Field Label"] == "Systolic"), None)
    assert sbp is not None
    assert sbp["Data Value"] == "145"
    assert map_variable(sbp) == "SBP"

    dbp = next((r for r in normalized if r["Field Label"] == "Diastolic"), None)
    assert dbp is not None
    assert dbp["Data Value"] == "92"
    assert map_variable(dbp) == "DBP"

    # Check combined GA at delivery
    ga_del = next((r for r in normalized if r["Field Label"] == "Gestational age at delivery"), None)
    assert ga_del is not None
    assert ga_del["Data Value"] == "38.4"
    assert map_variable(ga_del) == "GA_AT_DELIVERY"

    # Check pregnancy outcome
    preg_out = next((r for r in normalized if r["Field Label"] == "Pregnancy Outcome"), None)
    assert preg_out is not None
    assert preg_out["Data Value"] == "Normal baby"
    assert map_variable(preg_out) == "PREGNANCY_OUTCOME"

    # Check confirmed IUGR
    iugr = next((r for r in normalized if r["Field Label"] == "Confirmed IUGR?"), None)
    assert iugr is not None
    assert iugr["Data Value"] == "No"
    assert map_variable(iugr) == "CONFIRMED_IUGR"


def test_clinical_one_antenatal_ga_and_physical_exam_collation():
    from services.edc_mapping import normalize_clinical_one_rows
    from services.realtime_mapping import classify

    rows = [
        # Antenatal ultrasound GA weeks + days
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PREGNANCY ASSESSMENT",
            "Repeating Section Number": "N/A", "Question Label": "Weeks", "Value": "32",
            "Date & Time": "05-May-2026 11:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PREGNANCY ASSESSMENT",
            "Repeating Section Number": "N/A", "Question Label": "Days", "Value": "4",
            "Date & Time": "05-May-2026 11:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PREGNANCY ASSESSMENT",
            "Repeating Section Number": "N/A", "Question Label": "Fetal Weight", "Value": "1800",
            "Unit of Measure": "g", "Date & Time": "05-May-2026 11:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Physical Examination repeating section
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PHYSICAL EXAMINATION",
            "Repeating Section Number": "1", "Question Label": "System", "Value": "General Health Status",
            "Date & Time": "05-May-2026 11:30", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PHYSICAL EXAMINATION",
            "Repeating Section Number": "1", "Question Label": "Normal/Abnormal", "Value": "Abnormal",
            "Date & Time": "05-May-2026 11:30", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "PHYSICAL EXAMINATION",
            "Repeating Section Number": "1", "Question Label": "Abnormal findings description", "Value": "severe headache and facial oedema",
            "Date & Time": "05-May-2026 11:30", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Maternal Preeclampsia Assessment (restricted outcome)
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "MATERNAL PREECLAMPSIA ASSESSMENT",
            "Repeating Section Number": "N/A", "Question Label": "PE Status", "Value": "PE",
            "Date & Time": "05-May-2026 11:45", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        # Blinded biomarker test
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "BIOMARKER ANALYSIS",
            "Repeating Section Number": "1", "Question Label": "Lab Test", "Value": "Roche sFlt-1/PlGF ratio",
            "Date & Time": "05-May-2026 12:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        },
        {
            "Screening Number": "RWA001-0001", "Subject Number": "RWA001-0001",
            "Subject ID": "083319C03413466AA6151547A1693A38",
            "Visit/Event Title": "Visit 2", "Form Title": "BIOMARKER ANALYSIS",
            "Repeating Section Number": "1", "Question Label": "Lab Result", "Value": "85.2",
            "Date & Time": "05-May-2026 12:00", "Study Version": "1.3.0", "Type of Change": "CREATED", "User Name": "nurse@test.com"
        }
    ]

    normalized = list(normalize_clinical_one_rows(rows))

    # Verify combined antenatal GA
    ga_row = next((r for r in normalized if r["Export Variable Name"] == "ga_weeks"), None)
    assert ga_row is not None
    assert ga_row["Data Value"] == "32.6"
    assert map_variable(ga_row) == "GA_WEEKS"

    # Verify EFW
    efw_row = next((r for r in normalized if r["Field Label"] == "Fetal Weight"), None)
    assert efw_row is not None
    assert map_variable(efw_row) == "EFW"

    # Verify physical exam collation and findings
    pe_sys = next((r for r in normalized if r["Field Label"] == "General Health Status"), None)
    assert pe_sys is not None
    assert pe_sys["Data Value"] == "Abnormal"

    pe_find = next((r for r in normalized if "headache" in r["Field Label"].lower()), None)
    assert pe_find is not None
    assert "headache" in pe_find["Data Value"].lower()
    assert map_variable(pe_find) == "HEADACHE"

    # Verify PE Status restricted classification
    pe_status = next((r for r in normalized if r["Field Label"] == "PE Status"), None)
    assert pe_status is not None
    assert map_variable(pe_status) == "RECORDED_PE_STATUS"
    assert classify(pe_status) == "RESTRICTED_RECORDED_OUTCOME"

    # Verify blinded biomarker classification
    bio = next((r for r in normalized if "sFlt" in r["Field Label"]), None)
    assert bio is not None
    assert classify(bio) == "PROHIBITED_BLINDED"


