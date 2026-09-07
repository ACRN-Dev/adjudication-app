"""Controlled RealTime composite mapping and privacy classification."""
import re
from datetime import datetime, timezone

MAPPING_VERSION = "RT-MAP-1.0"
DIRECT_ALIASES = {
    "event_dt":"VISIT_DATE", "visit_date":"VISIT_DATE", "ga_event":"GA_WEEKS",
    "sbp":"SBP", "dbp":"DBP", "platelets":"PLATELETS", "plt":"PLATELETS",
    "creatinine":"CREATININE", "ast":"AST", "alt":"ALT", "ldh":"LDH",
    "upcr":"UPCR", "dipstick_protein":"DIPSTICK_PROTEIN", "headache":"HEADACHE",
    "visual_disturbance":"VISUAL_DISTURBANCE", "epigastric_pain":"EPIGASTRIC_PAIN",
    "pulmonary_edema":"PULMONARY_EDEMA", "eclampsia":"ECLAMPSIA",
}
PROHIBITED_PATTERNS = tuple(re.compile(p,re.I) for p in (
    r"s\s*flt[- ]?1", r"plgf", r"seng", r"biomarker", r"poc result",
    r"point.of.care", r"treatment allocation", r"randomi[sz]ation allocation", r"circa.?red",
))
DIRECT_IDENTIFIER_PATTERNS = tuple(re.compile(p,re.I) for p in (r"\bmrn\b", r"screening #", r"randomization #", r"randomisation #", r"date of birth", r"\bptid\b"))
RESTRICTED_PATTERNS = tuple(re.compile(p,re.I) for p in (r"electronic signature", r"research nurse", r"audit trail", r"file upload", r"reviewer"))

RULES = [
    ("VISIT_DATE", (r"visit date", r"date of visit")), ("ASSESSMENT_DATETIME", (r"assessment date",)),
    ("DATING_ANCHOR_DATE", (r"first sonographic date", r"first uss date")), ("DATING_ANCHOR_GA", (r"gestational age on first uss",)),
    ("EDD", (r"expected date of delivery", r"expected delivery date")), ("LMP", (r"last normal menstrual", r"\blmp\b")),
    ("GA_WEEKS", (r"gestational age.*weeks", r"weeks of gestation", r"\bga_weeks\b")), ("GA_DAYS", (r"gestational age.*days", r"\bga_days\b")),
    ("SBP_RECHECK", (r"systolic.*re.?check",)), ("DBP_RECHECK", (r"diastolic.*re.?check",)),
    ("SBP", (r"systolic blood pressure", r"\bsystolic\b")), ("DBP", (r"diastolic blood pressure", r"\bdiastolic\b")),
    ("HEART_RATE", (r"\bheart rate\b", r"\bpulse\b")), ("RESPIRATORY_RATE", (r"respiratory rate", r"\brespiration\b")),
    ("TEMPERATURE", (r"\btemperature\b",)), ("O2_SAT", (r"oxygen saturation", r"\bspo2\b")),
    ("DIPSTICK_DATE", (r"date.*urine dipstick",)), ("DIPSTICK_PROTEIN", (r"dipstick.*result", r"urine protein dipstick")),
    ("UPCR_PERFORMED", (r"protein.?creatinine ratio performed",)), ("UPCR", (r"\bupcr\b.*result", r"protein.?creatinine ratio result")),
    ("URINE_BLOOD", (r"\bblood\b.*urine", r"urine.*blood", r"^blood$")),
    ("URINE_KETONES", (r"\bketones\b",)), ("URINE_LEUKOCYTES", (r"\bleukocytes\b",)), ("URINE_NITRITES", (r"\bnitrites\b",)),
    ("PLATELETS", (r"platelet count", r"platelets")), ("CREATININE", (r"\bcreatinine\b",)),
    ("AST", (r"aspartate aminotransferase", r"\bast\b")), ("ALT", (r"alanine aminotransferase", r"\balt\b")), ("LDH", (r"lactate dehydrogenase", r"\bldh\b")),
    ("ALP", (r"alkaline phosphatase", r"\balp\b")), ("BILIRUBIN", (r"\bbilirubin\b",)), ("BUN", (r"blood urea nitrogen", r"\bbun\b")),
    ("HEMOGLOBIN", (r"\bhemoglobin\b", r"\bhb\b")), ("HEMATOCRIT", (r"\bhematocrit\b", r"\bhct\b")),
    ("WBC", (r"white blood cell count", r"\bwbc\b")), ("RBC", (r"red blood cell count", r"\brbc\b")), ("GLUCOSE", (r"\bglucose\b",)),
    ("RECORDED_PE_DIAGNOSIS_DATE", (r"preeclampsia diagnosis date", r"pe diagnosis date")),
    ("RECORDED_PE_DIAGNOSIS", (r"preeclampsia diagnosis description",)),
    ("RECORDED_PE_STATUS", (r"\bpe status\b", r"preeclampsia status")),
    ("RECORDED_PE_SYMPTOMS", (r"\bpe symptoms\b", r"preeclampsia symptoms")),
    ("HEADACHE", (r"headache",)), ("VISUAL_DISTURBANCE", (r"visual disturbance", r"blurred vision")), ("EPIGASTRIC_PAIN", (r"epigastric pain",)),
    ("PULMONARY_EDEMA", (r"pulmonary oedema", r"pulmonary edema")), ("ECLAMPSIA", (r"eclampsia", r"seizure")),
    ("ACUTE_RENAL_FAILURE", (r"acute renal failure", r"\barf\b")), ("DIC", (r"disseminated intravascular coagulation", r"\bdic\b")),
    ("CEREBRAL_HEMORRHAGE", (r"cerebral hemorrhage",)), ("CEREBRAL_THROMBOSIS", (r"cerebral thrombosis",)),
    ("MATERNAL_HOSPITALIZATION", (r"was the patient hospitalized",)), ("MATERNAL_ICU", (r"was the patient admitted to the icu",)),
    ("MATERNAL_DEATH", (r"maternal death",)),
    ("EFW", (r"fetal weight", r"estimated fetal weight")), ("IUGR", (r"^iugr$", r"intrauterine growth restriction")),
    ("AEDF", (r"absent end.diastolic",)), ("REDF", (r"reversed end.diastolic",)), ("AFI", (r"amniotic fluid index", r"^afi$", r"amniotic fluid volume")),
    ("CERVICAL_LENGTH", (r"cervical length",)), ("FETAL_HEART_RATE", (r"fetal heart rate",)),
    ("DELIVERY_DATE", (r"date of delivery", r"delivery date")), ("GA_AT_DELIVERY", (r"gestational age at delivery", r"^ga_at_delivery$", r"\bga_at_delivery\b")),
    ("PREGNANCY_OUTCOME", (r"pregnancy outcome",)), ("DELIVERY_TYPE", (r"type of delivery",)),
    ("CS_INDICATION", (r"reason for cesarean section", r"cesarean section indication")),
    ("ESTIMATED_BLOOD_LOSS", (r"estimated blood loss", r"\bebl\b")), ("BLOOD_TRANSFUSION", (r"blood transfusion",)),
    ("DELIVERY_LT_34W", (r"delivery <\s*34\s*weeks",)),
    ("CONFIRMED_IUGR", (r"confirmed iugr",)), ("CONFIRMED_SGA", (r"confirmed sga",)),
    ("IUGR_SGA_ASSESSMENT_DONE", (r"were iugr and sga assessments done",)),
    ("BIRTH_COMPLICATIONS", (r"birth complications",)), ("CONGENITAL_ANOMALIES", (r"congenital anomalies",)),
    ("NEONATAL_ICU_ADMISSION", (r"neonatal icu admission", r"was the neonate admitted to the icu")),
    ("NEONATAL_RDS", (r"respiratory distress syndrome", r"\brds\b")),
    ("NEONATAL_IVH", (r"intraventricular hemorrhage", r"\bivh\b")),
    ("NEONATAL_NEC", (r"necrotizing enterocolitis", r"\bnec\b")),
    ("APGAR_1MIN", (r"apgar score at 1 minute",)), ("APGAR_5MIN", (r"apgar score at 5 minutes",)), ("APGAR_10MIN", (r"apgar score at 10 minutes",)),
    ("BIRTH_WEIGHT", (r"birth weight",)),
    ("NEONATAL_GENDER", (r"^gender$", r"^sex$")), ("NEONATAL_LENGTH", (r"^length$",)), ("NEONATAL_HC", (r"head circumference",)),
    ("DELIVERY_OUTCOME", (r"delivery outcome",)), ("MATERNAL_OUTCOME", (r"maternal outcome",)), ("NEONATAL_OUTCOME", (r"neonatal outcome",)),
    ("MEDICATION_NAME", (r"medication name", r"drug name", r"concomitant medication", r"name of (?:the )?medication")),
    ("MEDICATION_DOSE", (r"medication dose", r"\bdose\b", r"dosage")),
    ("MEDICATION_ROUTE", (r"route of administration", r"\broute\b")),
    ("MEDICATION_INDICATION", (r"indication for medication", r"reason for (?:medication|drug)")),
    ("MEDICATION_START_DATE", (r"medication start date", r"start date.*medication")),
    ("MEDICATION_ONGOING", (r"medication ongoing", r"is.*medication.*ongoing")),
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
