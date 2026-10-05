with open("backend/services/realtime_mapping.py", "rb") as f:
    content = f.read()

# Replace in DIRECT_ALIASES
old_aliases = b'''DIRECT_ALIASES = {
    "event_dt":"visit_date", "visit_date":"visit_date", "ga_event":"ega_weeks",
    "sbp":"bp_systolic", "dbp":"bp_diastolic", "platelets":"platelets", "plt":"platelets",
    "creatinine":"creatinine", "ast":"ast", "alt":"alt", "ldh":"ldh",
    "upcr":"upcr", "dipstick_protein":"ua_protein", "headache":"headache",
    "visual_disturbance":"visual_disturbance", "epigastric_pain":"epigastric_pain",
    "pulmonary_edema":"pulmonary_edema", "eclampsia":"eclampsia",
}'''

new_aliases = b'''DIRECT_ALIASES = {
    "event_dt":"visit_date", "visit_date":"visit_date", "ga_event":"ega_weeks",
    "sbp":"bp_systolic", "dbp":"bp_diastolic", "platelets":"platelets", "plt":"platelets",
    "creatinine":"creatinine", "ast":"ast", "alt":"alt", "ldh":"ldh",
    "upcr":"upcr", "dipstick_protein":"ua_protein", "headache":"headache",
    "visual_disturbance":"visual_disturbance", "epigastric_pain":"epigastric_pain",
    "pulmonary_edema":"pulmonary_edema", "eclampsia":"eclampsia",
    "absolute_lymphocytes_count":"alc", "absolute_lymphocyte_count":"alc", "alc":"alc",
    "absolute_neutrophils_count":"anc", "absolute_neutrophil_count":"anc", "anc":"anc",
    "hematocrit":"haematocrit", "haematocrit":"haematocrit", "hct":"haematocrit",
}'''

# Normalize newlines for matching
content_normalized = content.replace(b"\r\n", b"\n")
old_norm = old_aliases.replace(b"\r\n", b"\n")
new_norm = new_aliases.replace(b"\r\n", b"\n")

assert old_norm in content_normalized, "old_aliases not found!"
content_normalized = content_normalized.replace(old_norm, new_norm, 1)

# Replace in RULES
old_rules = b'''    ("haemoglobin", (r"\\bhemoglobin\\b", r"\\bhaemoglobin\\b", r"\\bhb\\b")), ("haematocrit", (r"\\bhematocrit\\b", r"\\bhct\\b")),
    ("wbc", (r"white blood cell count", r"\\bwbc\\b")), ("rbc", (r"red blood cell count", r"\\brbc\\b")), ("glucose", (r"\\bglucose\\b",)),
    ("anc", (r"absolute neutrophil count", r"\\banc\\b", r"neutrophil count", r"^neutrophils$")),
    ("alc", (r"absolute lymphocyte count", r"\\balc\\b", r"lymphocyte count", r"^lymphocytes$")),'''

new_rules = b'''    ("haemoglobin", (r"\\bhemoglobin\\b", r"\\bhaemoglobin\\b", r"\\bhb\\b")), ("haematocrit", (r"\\bhaematocrit\\b", r"\\bhematocrit\\b", r"\\bhct\\b", r"\\bpcv\\b")),
    ("wbc", (r"white blood cell count", r"\\bwbc\\b")), ("rbc", (r"red blood cell count", r"\\brbc\\b")), ("glucose", (r"\\bglucose\\b",)),
    ("anc", (r"absolute neutrophils?\\s*count", r"\\banc\\b", r"neutrophils?\\s*count", r"^neutrophils?$")),
    ("alc", (r"absolute lymphocytes?\\s*count", r"\\balc\\b", r"lymphocytes?\\s*count", r"^lymphocytes?$")),'''

old_rules_norm = old_rules.replace(b"\r\n", b"\n")
new_rules_norm = new_rules.replace(b"\r\n", b"\n")

assert old_rules_norm in content_normalized, "old_rules not found!"
content_normalized = content_normalized.replace(old_rules_norm, new_rules_norm, 1)

# Also in interpretation rules
old_interp = b'''("platelets", r"platelets?"), ("anc", r"neutrophil|\\banc\\b"), ("alc", r"lymphocyte|\\balc\\b"),'''
new_interp = b'''("platelets", r"platelets?"), ("anc", r"neutrophils?|\\banc\\b"), ("alc", r"lymphocytes?|\\balc\\b"),'''

assert old_interp in content_normalized, "old_interp not found!"
content_normalized = content_normalized.replace(old_interp, new_interp, 1)

with open("backend/services/realtime_mapping.py", "wb") as f:
    f.write(content_normalized)

print("Successfully updated backend/services/realtime_mapping.py")
