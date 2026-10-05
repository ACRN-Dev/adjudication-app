import re

NON_RESULT_PATTERNS = tuple(re.compile(p, re.I) for p in (
    r"result interpretation", r"normal/abnormal", r"comment", r"low range", r"high range",
    r"file upload", r"electronic signature", r"qc \(lab\)", r"initials", r"reviewer's comments",
    r"^were vital signs performed", r"^vital signs recheck needed",
    r"new onset of elevated bp", r"proteinuria.*dipstick.*elevated bp",
    r"^attempt$", r"^first attempt", r"^second attempt",
))

DIRECT_ALIASES = {
    "event_dt":"visit_date", "visit_date":"visit_date", "ga_event":"ega_weeks",
    "sbp":"bp_systolic", "dbp":"bp_diastolic", "platelets":"platelets", "plt":"platelets",
    "creatinine":"creatinine", "ast":"ast", "alt":"alt", "ldh":"ldh",
    "upcr":"upcr", "dipstick_protein":"ua_protein", "headache":"headache",
    "visual_disturbance":"visual_disturbance", "epigastric_pain":"epigastric_pain",
    "pulmonary_edema":"pulmonary_edema", "eclampsia":"eclampsia",
}

RULES = [
    ("dating_anchor_date", (r"first sonographic date", r"first uss date")),
    ("dating_anchor_ga", (r"gestational age on first uss", r"gestational age on scan")),
    ("ega_delivery", (r"gestational age at delivery", r"\bga_at_delivery\b", r"na_gestage", r"do_gestage")),
    ("ega_days", (r"current gestational age.*days", r"gestational age.*days", r"\bga_days\b", r"gestageday")),
    ("ega_weeks", (r"current gestational age.*weeks", r"current gestational age", r"gestational age.*weeks", r"weeks of gestation", r"\bga_weeks\b", r"gestagewk")),
    ("age", (r"^age$", r"\bpatient age\b", r"\bage at enrollment\b", r"\bage_years\b")),
    ("gravida", (r"how many previous\s*pregnancies",)),
    ("para_live", (r"number of live births",)), ("para_miscarriage", (r"number of miscarriages",)),
    ("previous_cs", (r"number of cesarean sections",)),
    ("visit_date", (r"visit date", r"date of visit", r"date of the visit")), ("assessment_datetime", (r"assessment date",)),
    ("edd", (r"expected date of delivery", r"expected delivery date")), ("lmp", (r"last normal menstrual", r"\blmp\b")),
    
    # Specific PE symptoms/screening questions before vitals
    ("pe_symptom_elevated_sbp", (r"elevated.*systolic.*blood pressure", r"^elevated systolic\b")),
    ("pe_symptom_elevated_dbp", (r"elevated.*diastolic.*blood pressure", r"^elevated diastolic\b")),
    ("pe_symptom_sudden_weight_gain", (r"sudden weight gain",)),
    
    # Fetal / Neonatal measurements before maternal vitals
    ("fetal_heart_rate", (r"fetal heart rate", r"\bfhr\b")),
    ("efw", (r"fetal weight", r"estimated fetal weight", r"estimated us fetal weight", r"us fetal weight")),
    ("newborn_weight_g", (r"birth weight", r"neonatal weight")),
    
    # Maternal vitals
    ("bp_systolic_recheck", (r"systolic blood pressure recheck", r"^systolic.*re.?check")),
    ("bp_diastolic_recheck", (r"diastolic blood pressure recheck", r"^diastolic.*re.?check")),
    ("bp_systolic", (r"^systolic blood pressure$", r"^systolic bp$", r"^systolic$", r"\bsystolic blood pressure\b")),
    ("bp_diastolic", (r"^diastolic blood pressure$", r"^diastolic bp$", r"^diastolic$", r"\bdiastolic blood pressure\b")),
    ("heart_rate", (r"^heart rate$", r"^pulse$", r"\bmaternal heart rate\b", r"\bmaternal pulse\b")),
    ("respiratory_rate", (r"respiratory rate", r"\brespiration\b")),
    ("temperature", (r"body temperature", r"\btemperature\b")),
    ("weight", (r"^weight$", r"^maternal weight$", r"\bmaternal weight\b")),
    ("height", (r"^height$", r"^maternal height$", r"\bmaternal height\b")),
    ("bmi", (r"^bmi$", r"body mass index")),
    ("o2_sat", (r"oxygen saturation", r"\bspo2\b")),
    
    ("ua_blood", (r"urine blood results", r"\bblood\b.*urine", r"urine.*blood", r"\bblood\b")),
    ("ua_ketones", (r"urine ketones results", r"\bketones\b")),
    ("ua_leukocytes", (r"urine leukocytes results", r"\bleukocytes\b")),
    ("ua_nitrites", (r"urine nitrites results", r"\bnitrites\b")),
    ("ua_protein", (r"urine protein results", r"dipstick.*result", r"urine protein dipstick")),
    ("ua_glucose", (r"urine glucose results", r"\burine glucose\b")),
    ("upcr", (r"\bupcr\b.*result", r"protein.?creatinine ratio result")),
    ("platelets", (r"platelets count", r"platelet count", r"\bplatelets\b")),
    ("creatinine", (r"creatinine result", r"\bcreatinine\b")),
    ("ast", (r"aspartate aminotransferase", r"\bast\b")),
    ("alt", (r"alanine aminotransferase", r"\balt\b")),
    ("ldh", (r"lactate dehydrogenase", r"\bldh\b")),
    ("alp", (r"alkaline phosphatase", r"\balp\b")),
    ("total_bilirubin", (r"total bilirubin result", r"\bbilirubin\b")),
    ("bun", (r"blood urea nitrogen", r"\bbun\b")),
    ("haemoglobin", (r"\bhemoglobin\b", r"\bhaemoglobin\b", r"\bhb\b")),
    ("haematocrit", (r"\bhematocrit\b", r"\bhct\b")),
    ("wbc", (r"white blood cell count", r"\bwbc\b")),
    ("rbc", (r"red blood cell count", r"\brbc\b")),
    ("glucose", (r"\bglucose\b",)),
    ("RECORDED_PE_DIAGNOSIS_DATE", (r"preeclampsia diagnosis date", r"pe diagnosis date")),
    ("RECORDED_PE_DIAGNOSIS", (r"preeclampsia diagnosis description",)),
    ("RECORDED_PE_STATUS", (r"\bpe status\b", r"preeclampsia status")),
    ("RECORDED_PE_SYMPTOMS", (r"\bpe symptoms\b", r"preeclampsia symptoms")),
    ("headache", (r"headache",)),
    ("visual_disturbance", (r"visual disturbance", r"blurred vision")),
    ("epigastric_pain", (r"epigastric pain",)),
    ("pulmonary_edema", (r"pulmonary oedema", r"pulmonary edema")),
    ("eclampsia", (r"eclampsia", r"seizure")),
    ("acute_renal_failure", (r"acute renal failure", r"\barf\b")),
    ("dic", (r"disseminated intravascular coagulation", r"\bdic\b")),
    ("cerebral_hemorrhage", (r"cerebral hemorrhage",)),
    ("cerebral_thrombosis", (r"cerebral thrombosis",)),
    ("maternal_hospitalization", (r"was the patient hospitalized",)),
    ("maternal_icu", (r"was the patient admitted to the icu",)),
    ("maternal_death", (r"maternal death",)),
    ("iugr", (r"^iugr$", r"intrauterine growth restriction")),
    ("ua_aedf", (r"absent end.diastolic",)),
    ("ua_redf", (r"reversed end.diastolic",)),
    ("afi", (r"amniotic fluid index", r"^afi$", r"amniotic fluid volume")),
    ("cervical_length", (r"cervical length",)),
    ("delivery_date", (r"date of delivery", r"delivery date")),
    ("pregnancy_outcome", (r"pregnancy outcome",)),
    ("delivery_mode", (r"type of delivery",)),
    ("indication", (r"reason for cesarean section", r"cesarean section indication")),
    ("ebl_ml", (r"estimated blood loss", r"\bebl\b")),
    ("blood_transfusion", (r"blood transfusion",)),
    ("delivery_lt_34w", (r"delivery <\s*34\s*weeks",)),
    ("confirmed_iugr", (r"confirmed iugr",)),
    ("confirmed_sga", (r"confirmed sga",)),
    ("iugr_sga_assessment_done", (r"were iugr and sga assessments done",)),
    ("birth_complications", (r"birth complications",)),
    ("congenital_anomalies", (r"congenital anomalies",)),
    ("neonatal_icu_admission", (r"neonatal icu admission", r"was the neonate admitted to the icu")),
    ("neonatal_rds", (r"respiratory distress syndrome", r"\brds\b")),
    ("neonatal_ivh", (r"intraventricular hemorrhage", r"\bivh\b")),
    ("neonatal_nec", (r"necrotizing enterocolitis", r"\bnec\b")),
    ("apgar_1m", (r"apgar score at 1 minute",)),
    ("apgar_5m", (r"apgar score at 5 minutes",)),
    ("apgar_10m", (r"apgar score at 10 minutes",)),
    ("neonatal_gender", (r"^gender$", r"^sex$")),
    ("neonatal_length", (r"^length$",)),
    ("neonatal_hc", (r"head circumference",)),
    ("delivery_outcome", (r"delivery outcome",)),
    ("maternal_outcome", (r"maternal outcome",)),
    ("neonatal_outcome", (r"neonatal outcome",)),
    ("medication_name", (r"medication name", r"drug name", r"concomitant medication", r"name of (?:the )?medication")),
    ("medication_dose", (r"medication dose", r"\bdose\b", r"dosage")),
    ("medication_route", (r"route of administration", r"\broute\b")),
    ("medication_indication", (r"indication for medication", r"reason for (?:medication|drug)")),
    ("medication_start_date", (r"medication start date", r"start date.*medication")),
    ("medication_ongoing", (r"medication ongoing", r"is.*medication.*ongoing")),
]
COMPILED_RULES = [(c, tuple(re.compile(p, re.I) for p in pats)) for c, pats in RULES]

def norm(value): return re.sub(r"\s+", " ", str(value or "").strip().lower())

def map_variable_test(row):
    field_text = norm(row.get("Field Label"))
    if not field_text or any(p.search(field_text) for p in NON_RESULT_PATTERNS):
        return None
    page_text = norm(row.get("Page Title"))
    if any(p.search(page_text) for p in NON_RESULT_PATTERNS):
        return None
    export_name = norm(row.get("Export Variable Name")).replace(" ", "_")
    if export_name in DIRECT_ALIASES:
        return DIRECT_ALIASES[export_name]

    # Specific context overrides
    if "newborn" in page_text or "neonatal" in page_text:
        if field_text == "heart rate":
            return "neonatal_heart_rate"
        if field_text in {"weight", "birth weight"}:
            return "newborn_weight_g"
        if field_text in {"gestational age", "gestational age at delivery"}:
            return "ega_delivery"

    # Match against Field Label and Export Variable Name first (specific)
    for canonical, patterns in COMPILED_RULES:
        if any(p.search(field_text) or (export_name and p.search(export_name)) for p in patterns):
            return canonical

    # Then fallback to broader text (Page Title + Field Label + Export Variable Name)
    # but exclude generic page titles for vitals
    text = " | ".join(norm(row.get(k)) for k in ("Page Title", "Field Label", "Export Variable Name"))
    for canonical, patterns in COMPILED_RULES:
        if canonical in {"weight", "height", "bmi", "o2_sat", "heart_rate", "respiratory_rate", "temperature", "bp_systolic", "bp_diastolic"}:
            continue
        if any(p.search(text) for p in patterns):
            return canonical
    return None

test_cases = [
    ("Vital Signs/Weight Height", "Height", "height"),
    ("Vital Signs/Weight Height", "Weight", "weight"),
    ("Vital Signs/Weight Height", "BMI", "bmi"),
    ("Vital Signs/Weight Height", "Oxygen saturation", "o2_sat"),
    ("Vital Signs/Weight Height", "Heart rate", "heart_rate"),
    ("Vital Signs/Weight Height", "Pulse", "heart_rate"),
    ("Vital Signs/Weight Height", "Body temperature", "temperature"),
    ("Vital Signs/Weight Height", "Systolic blood pressure", "bp_systolic"),
    ("Vital Signs/Weight Height", "Diastolic blood pressure", "bp_diastolic"),
    ("Vital Signs/Weight Height", "Systolic blood pressure recheck", "bp_systolic_recheck"),
    ("Vital signs/ Weight", "Weight", "weight"),
    ("Vital signs/ Weight", "Heart rate", "heart_rate"),
    ("Vital signs/ Weight", "Systolic blood pressure", "bp_systolic"),
    ("Vital signs/ Weight", "Diastolic blood pressure", "bp_diastolic"),
    ("Pregnancy Assessment", "Current Gestational Age  (calculated using first USS)", "ega_weeks"),
    ("Pregnancy Assessment", "Current Gestational Age (claculated using first USS)", "ega_weeks"),
    ("Maternal Preeclampsia Assessment", "Elevated systolic blood pressure?", "pe_symptom_elevated_sbp"),
    ("Maternal Preeclampsia Assessment", "Elevated diastolic blood pressure?", "pe_symptom_elevated_dbp"),
    ("Maternal Preeclampsia Assessment", "Sudden weight gain (>1 kg/week in the third trimester)?", "pe_symptom_sudden_weight_gain"),
    ("Sonographic Data", "US Fetal Weight", "efw"),
    ("Sonographic Data", "Estimated US Fetal Weight", "efw"),
    ("Sonographic Data", "Fetal heart rate", "fetal_heart_rate"),
    ("Newborn Assessment Form", "Birth Weight", "newborn_weight_g"),
    ("Newborn Assessment Form", "Heart rate", "neonatal_heart_rate"),
    ("Newborn Assessment Form", "Heart", None),
    ("Newborn Assessment Form", "Heart Examination Description", None),
    ("Inclusion/Exclusion", "a. New onset of elevated BP (systolic BP ? 130mmHg or DBP ? 80)", None),
    ("Screening |V01", "Were vital signs performed?", None),
]

passed = 0
for page, label, expected in test_cases:
    actual = map_variable_test({"Page Title": page, "Field Label": label, "Export Variable Name": ""})
    status = "OK" if actual == expected else f"FAIL (got {actual}, expected {expected})"
    if actual == expected:
        passed += 1
    print(f"[{status}] Page: {page} | Label: {label} -> {actual}")

print(f"\n{passed}/{len(test_cases)} tests passed.")
