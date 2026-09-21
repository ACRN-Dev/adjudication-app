"""Controlled RealTime composite mapping and privacy classification."""
import re
from datetime import datetime, timezone

MAPPING_VERSION = "RT-MAP-2.0"
DIRECT_ALIASES = {
    "event_dt":"visit_date", "visit_date":"visit_date", "ga_event":"ega_weeks",
    "sbp":"bp_systolic", "dbp":"bp_diastolic", "platelets":"platelets", "plt":"platelets",
    "creatinine":"creatinine", "ast":"ast", "alt":"alt", "ldh":"ldh",
    "upcr":"upcr", "dipstick_protein":"ua_protein", "headache":"headache",
    "visual_disturbance":"visual_disturbance", "epigastric_pain":"epigastric_pain",
    "pulmonary_edema":"pulmonary_edema", "eclampsia":"eclampsia",
}
PROHIBITED_PATTERNS = tuple(re.compile(p,re.I) for p in (
    r"s\s*flt[- ]?1", r"plgf", r"seng", r"biomarker", r"poc result",
    r"point.of.care", r"treatment allocation", r"randomi[sz]ation allocation", r"circa.?red",
))
DIRECT_IDENTIFIER_PATTERNS = tuple(re.compile(p,re.I) for p in (r"\bmrn\b", r"screening #", r"randomization #", r"randomisation #", r"date of birth", r"\bptid\b"))
RESTRICTED_PATTERNS = tuple(re.compile(p,re.I) for p in (r"electronic signature", r"research nurse", r"audit trail", r"file upload", r"reviewer"))
NON_RESULT_PATTERNS = tuple(re.compile(p,re.I) for p in (
    r"result interpretation", r"normal/abnormal", r"comment", r"low range", r"high range",
    r"file upload", r"electronic signature", r"qc \(lab\)", r"initials", r"reviewer's comments",
))

RULES = [
    ("age", (r"^age$",)), ("gravida", (r"how many previous\s*pregnancies",)),
    ("para_live", (r"number of live births",)), ("para_miscarriage", (r"number of miscarriages",)),
    ("previous_cs", (r"number of cesarean sections",)),
    ("visit_date", (r"visit date", r"date of visit", r"date of the visit")), ("assessment_datetime", (r"assessment date",)),
    ("dating_anchor_date", (r"first sonographic date", r"first uss date")), ("dating_anchor_ga", (r"gestational age on first uss",)),
    ("edd", (r"expected date of delivery", r"expected delivery date")), ("lmp", (r"last normal menstrual", r"\blmp\b")),
    ("ega_days", (r"current gestational age.*days", r"gestational age.*days", r"\bga_days\b")), ("ega_weeks", (r"current gestational age", r"gestational age.*weeks", r"weeks of gestation", r"\bga_weeks\b")),
    ("bp_systolic_recheck", (r"systolic blood pressure recheck", r"systolic.*re.?check")), ("bp_diastolic_recheck", (r"diastolic blood pressure recheck", r"diastolic.*re.?check")),
    ("bp_systolic", (r"^systolic blood pressure$", r"\bsystolic\b")), ("bp_diastolic", (r"^diastolic blood pressure$", r"\bdiastolic\b")),
    ("heart_rate", (r"^heart rate$", r"\bpulse\b")), ("respiratory_rate", (r"respiratory rate", r"\brespiration\b")),
    ("temperature", (r"body temperature", r"\btemperature\b")), ("weight", (r"^weight$",)), ("o2_sat", (r"oxygen saturation", r"\bspo2\b")),
    ("ua_blood", (r"urine blood results", r"\bblood\b.*urine", r"urine.*blood", r"^blood$")), ("ua_ketones", (r"urine ketones results", r"\bketones\b")),
    ("ua_leukocytes", (r"urine leukocytes results", r"\bleukocytes\b")), ("ua_nitrites", (r"urine nitrites results", r"\bnitrites\b")),
    ("ua_protein", (r"urine protein results", r"dipstick.*result", r"urine protein dipstick")), ("ua_glucose", (r"urine glucose results", r"\burine glucose\b")),
    ("upcr", (r"\bupcr\b.*result", r"protein.?creatinine ratio result")),
    ("platelets", (r"platelets count", r"platelet count", r"\bplatelets\b")), ("creatinine", (r"creatinine result", r"\bcreatinine\b")),
    ("ast", (r"aspartate aminotransferase", r"\bast\b")), ("alt", (r"alanine aminotransferase", r"\balt\b")), ("ldh", (r"lactate dehydrogenase", r"\bldh\b")),
    ("alp", (r"alkaline phosphatase", r"\balp\b")), ("total_bilirubin", (r"total bilirubin result", r"\bbilirubin\b")), ("bun", (r"blood urea nitrogen", r"\bbun\b")),
    ("haemoglobin", (r"^hemoglobin$", r"^haemoglobin$", r"\bhb\b")), ("haematocrit", (r"^hematocrit$", r"\bhct\b")),
    ("wbc", (r"white blood cell count", r"\bwbc\b")), ("rbc", (r"red blood cell count", r"\brbc\b")), ("glucose", (r"\bglucose\b",)),
    ("RECORDED_PE_DIAGNOSIS_DATE", (r"preeclampsia diagnosis date", r"pe diagnosis date")),
    ("RECORDED_PE_DIAGNOSIS", (r"preeclampsia diagnosis description",)),
    ("RECORDED_PE_STATUS", (r"\bpe status\b", r"preeclampsia status")),
    ("RECORDED_PE_SYMPTOMS", (r"\bpe symptoms\b", r"preeclampsia symptoms")),
    ("headache", (r"headache",)), ("visual_disturbance", (r"visual disturbance", r"blurred vision")), ("epigastric_pain", (r"epigastric pain",)),
    ("pulmonary_edema", (r"pulmonary oedema", r"pulmonary edema")), ("eclampsia", (r"eclampsia", r"seizure")),
    ("acute_renal_failure", (r"acute renal failure", r"\barf\b")), ("dic", (r"disseminated intravascular coagulation", r"\bdic\b")),
    ("cerebral_hemorrhage", (r"cerebral hemorrhage",)), ("cerebral_thrombosis", (r"cerebral thrombosis",)),
    ("maternal_hospitalization", (r"was the patient hospitalized",)), ("maternal_icu", (r"was the patient admitted to the icu",)),
    ("maternal_death", (r"maternal death",)),
    ("efw", (r"fetal weight", r"estimated fetal weight")), ("iugr", (r"^iugr$", r"intrauterine growth restriction")),
    ("ua_aedf", (r"absent end.diastolic",)), ("ua_redf", (r"reversed end.diastolic",)), ("afi", (r"amniotic fluid index", r"^afi$", r"amniotic fluid volume")),
    ("cervical_length", (r"cervical length",)), ("fetal_heart_rate", (r"fetal heart rate",)),
    ("delivery_date", (r"date of delivery", r"delivery date")), ("ega_delivery", (r"gestational age at delivery", r"^ga_at_delivery$", r"\bga_at_delivery\b")),
    ("pregnancy_outcome", (r"pregnancy outcome",)), ("delivery_mode", (r"type of delivery",)),
    ("indication", (r"reason for cesarean section", r"cesarean section indication")),
    ("ebl_ml", (r"estimated blood loss", r"\bebl\b")), ("blood_transfusion", (r"blood transfusion",)),
    ("delivery_lt_34w", (r"delivery <\s*34\s*weeks",)),
    ("confirmed_iugr", (r"confirmed iugr",)), ("confirmed_sga", (r"confirmed sga",)),
    ("iugr_sga_assessment_done", (r"were iugr and sga assessments done",)),
    ("birth_complications", (r"birth complications",)), ("congenital_anomalies", (r"congenital anomalies",)),
    ("neonatal_icu_admission", (r"neonatal icu admission", r"was the neonate admitted to the icu")),
    ("neonatal_rds", (r"respiratory distress syndrome", r"\brds\b")),
    ("neonatal_ivh", (r"intraventricular hemorrhage", r"\bivh\b")),
    ("neonatal_nec", (r"necrotizing enterocolitis", r"\bnec\b")),
    ("apgar_1m", (r"apgar score at 1 minute",)), ("apgar_5m", (r"apgar score at 5 minutes",)), ("apgar_10m", (r"apgar score at 10 minutes",)),
    ("newborn_weight_g", (r"birth weight",)),
    ("neonatal_gender", (r"^gender$", r"^sex$")), ("neonatal_length", (r"^length$",)), ("neonatal_hc", (r"head circumference",)),
    ("delivery_outcome", (r"delivery outcome",)), ("maternal_outcome", (r"maternal outcome",)), ("neonatal_outcome", (r"neonatal outcome",)),
    ("medication_name", (r"medication name", r"drug name", r"concomitant medication", r"name of (?:the )?medication")),
    ("medication_dose", (r"medication dose", r"\bdose\b", r"dosage")),
    ("medication_route", (r"route of administration", r"\broute\b")),
    ("medication_indication", (r"indication for medication", r"reason for (?:medication|drug)")),
    ("medication_start_date", (r"medication start date", r"start date.*medication")),
    ("medication_ongoing", (r"medication ongoing", r"is.*medication.*ongoing")),
]
RULES=[(canonical,tuple(re.compile(p,re.I) for p in patterns)) for canonical,patterns in RULES]

def norm(value): return re.sub(r"\s+", " ", str(value or "").strip().lower())
def metadata_text(row): return " | ".join(norm(row.get(k)) for k in ("Form Title","Form Version","Page Title","Field Label","Field type","Export Variable Name"))
def classify(row):
    text=metadata_text(row)
    if any(p.search(text) for p in PROHIBITED_PATTERNS): return "PROHIBITED_BLINDED"
    if any(p.search(text) for p in DIRECT_IDENTIFIER_PATTERNS): return "DIRECT_IDENTIFIER"
    if (map_variable(row) or "").startswith("RECORDED_PE_"): return "RESTRICTED_RECORDED_OUTCOME"
    if any(p.search(text) for p in RESTRICTED_PATTERNS): return "RESTRICTED_OPERATIONAL_METADATA"
    return "PERMITTED_CLINICAL_EVIDENCE" if map_variable(row) else "UNMAPPED"
def map_variable(row):
    field_text = norm(row.get("Field Label"))
    if any(pattern.search(field_text) for pattern in NON_RESULT_PATTERNS):
        return None
    export_name=norm(row.get("Export Variable Name")).replace(" ", "_")
    if export_name in DIRECT_ALIASES: return DIRECT_ALIASES[export_name]
    text=" | ".join(norm(row.get(k)) for k in ("Page Title","Field Label","Export Variable Name"))
    for canonical,patterns in RULES:
        if any(p.search(text) for p in patterns): return canonical
    return None
def source_value(row): return (row.get("Data Value") or row.get("Data Input") or "").strip()
def parse_datetime(value):
    v=(value or "").strip().split("|")[0].strip()
    if not v: return None
    normalized=re.sub(r"\s+(?:SAST|SAT|UTC|GMT)$", "", v, flags=re.I).strip()
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    for fmt in (
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%d/%b/%Y %H:%M:%S", "%d/%b/%Y %H:%M",
        "%d/%b/%Y %I:%M:%S %p", "%d/%b/%Y %I:%M %p", "%d/%b/%Y",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y",
    ):
        try: return datetime.strptime(normalized,fmt)
        except ValueError: pass
    return None
def parse_numeric(value):
    m=re.search(r"[-+]?\d+(?:\.\d+)?",str(value or "").replace(",",""))
    try: return float(m.group()) if m else None
    except ValueError: return None
def parse_coded(value):
    v=norm(value)
    if v in {"yes","y","true","1"}: return "YES"
    if v in {"no","n","false","0"}: return "NO"
    if "not done" in v: return "NOT_DONE"
    if "not applicable" in v: return "NOT_APPLICABLE"
    if "unknown" in v: return "UNKNOWN"
    if "not answered" in v: return "MISSING"
    return str(value or "").strip() or None
def visit_code(form_title):
    text=norm(form_title)
    if "screening" in text or "v01" in text: return "V01",1,"SCHEDULED"
    m=re.search(r"visit\s*(\d+)",text)
    if m: return f"V{int(m.group(1)):02d}",int(m.group(1)),"SCHEDULED"
    if "unscheduled" in text: return "UNSCHEDULED",90,"UNSCHEDULED"
    if "early termination" in text: return "EARLY_TERMINATION",95,"EARLY_TERMINATION"
    if "adverse event" in text: return "ADVERSE_EVENT",96,"EVENT"
    if "protocol deviation" in text: return "PROTOCOL_DEVIATION",97,"EVENT"
    return "OTHER",99,"OTHER"
