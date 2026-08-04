"""Controlled RealTime composite mapping and privacy classification."""
import re
from datetime import datetime

MAPPING_VERSION = "RT-MAP-1.0"
PROHIBITED_PATTERNS = tuple(re.compile(p,re.I) for p in (
    r"s\s*flt[- ]?1", r"plgf", r"seng", r"biomarker", r"poc result",
    r"point.of.care", r"treatment allocation", r"randomi[sz]ation allocation", r"circa.?red",
))
DIRECT_IDENTIFIER_PATTERNS = tuple(re.compile(p,re.I) for p in (r"\bmrn\b", r"screening #", r"randomization #", r"randomisation #", r"date of birth", r"\bptid\b"))
RESTRICTED_PATTERNS = tuple(re.compile(p,re.I) for p in (r"electronic signature", r"research nurse", r"audit trail", r"file upload", r"reviewer"))

RULES = [
 ("VISIT_DATE", (r"visit date", r"date of visit")), ("ASSESSMENT_DATETIME", (r"assessment date",)),
 ("DATING_ANCHOR_DATE", (r"first sonographic date", r"first uss date")), ("DATING_ANCHOR_GA", (r"gestational age on first uss",)),
 ("EDD", (r"expected date of delivery", r"expected delivery date",)), ("LMP", (r"last normal menstrual", r"\blmp\b")),
 ("GA_WEEKS", (r"gestational age.*weeks", r"weeks of gestation")), ("GA_DAYS", (r"gestational age.*days",)),
 ("SBP_RECHECK", (r"systolic.*re.?check",)), ("DBP_RECHECK", (r"diastolic.*re.?check",)),
 ("SBP", (r"systolic blood pressure",)), ("DBP", (r"diastolic blood pressure",)),
 ("DIPSTICK_DATE", (r"date.*urine dipstick",)), ("DIPSTICK_PROTEIN", (r"dipstick.*result", r"urine protein dipstick")),
 ("UPCR_PERFORMED", (r"protein.?creatinine ratio performed",)), ("UPCR", (r"\bupcr\b.*result", r"protein.?creatinine ratio result")),
 ("PLATELETS", (r"platelet count", r"platelets")), ("CREATININE", (r"\bcreatinine\b",)),
 ("AST", (r"aspartate aminotransferase", r"\bast\b")), ("ALT", (r"alanine aminotransferase", r"\balt\b")), ("LDH", (r"lactate dehydrogenase", r"\bldh\b")),
 ("RECORDED_PE_DIAGNOSIS_DATE", (r"preeclampsia diagnosis date", r"pe diagnosis date")),
 ("RECORDED_PE_DIAGNOSIS", (r"preeclampsia diagnosis description",)), ("RECORDED_PE_STATUS", (r"^pe status$", r"preeclampsia status")),
 ("HEADACHE", (r"headache",)), ("VISUAL_DISTURBANCE", (r"visual disturbance", r"blurred vision")), ("EPIGASTRIC_PAIN", (r"epigastric pain",)),
 ("PULMONARY_EDEMA", (r"pulmonary oedema", r"pulmonary edema")), ("ECLAMPSIA", (r"eclampsia", r"seizure")),
 ("EFW", (r"fetal weight", r"estimated fetal weight")), ("IUGR", (r"confirmed iugr", r"intrauterine growth restriction")),
 ("AEDF", (r"absent end.diastolic",)), ("REDF", (r"reversed end.diastolic",)), ("AFI", (r"amniotic fluid index", r"^afi$")),
 ("DELIVERY_DATE", (r"date of delivery", r"delivery date")), ("GA_AT_DELIVERY", (r"gestational age at delivery",)),
 ("DELIVERY_OUTCOME", (r"delivery outcome",)), ("MATERNAL_OUTCOME", (r"maternal outcome",)), ("NEONATAL_OUTCOME", (r"neonatal outcome",)),
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
    text=" | ".join(norm(row.get(k)) for k in ("Page Title","Field Label","Export Variable Name"))
    for canonical,patterns in RULES:
        if any(p.search(text) for p in patterns): return canonical
    return None
def source_value(row): return (row.get("Data Value") or row.get("Data Input") or "").strip()
def parse_datetime(value):
    v=(value or "").strip().split("|")[0].strip()
    for fmt in ("%m/%d/%Y %H:%M:%S","%m/%d/%Y %H:%M","%d/%b/%Y %I:%M:%S %p %Z","%d/%b/%Y","%Y-%m-%d","%d-%b-%Y"):
        try: return datetime.strptime(v,fmt)
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
