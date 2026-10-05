import sys
sys.path.insert(0, 'backend')
import services.realtime_mapping as rm

def map_variable_clean(row):
    field_text = rm.norm(row.get("Field Label"))
    if any(pattern.search(field_text) for pattern in rm.NON_RESULT_PATTERNS):
        return None
    export_name = rm.norm(row.get("Export Variable Name")).replace(" ", "_")
    if export_name in rm.DIRECT_ALIASES:
        return rm.DIRECT_ALIASES[export_name]
        
    # Match against Field Label and Export Variable Name first (specific)
    for canonical, patterns in rm.RULES:
        if any(p.search(field_text) or (export_name and p.search(export_name)) for p in patterns):
            return canonical
            
    # Then fallback to broader text (Page Title + Field Label + Export Variable Name)
    # but exclude generic page titles for vitals like 'weight', 'height', 'bmi', 'pulse'
    text = " | ".join(rm.norm(row.get(k)) for k in ("Page Title", "Field Label", "Export Variable Name"))
    for canonical, patterns in rm.RULES:
        if canonical in {"weight", "height", "bmi", "o2_sat", "heart_rate"}:
            continue
        if any(p.search(text) for p in patterns):
            return canonical
    return None

test_rows = [
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Height", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Weight", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "BMI", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Oxygen saturation", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Heart rate", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Pulse", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Body temperature", "Export Variable Name": ""},
    {"Page Title": "Vital Signs/Weight Height", "Field Label": "Systolic blood pressure", "Export Variable Name": ""},
    {"Page Title": "Pregnancy Assessment", "Field Label": "Current Gestational Age  (calculated using first USS)", "Export Variable Name": ""},
]

for r in test_rows:
    print(f"{r['Field Label']} -> {map_variable_clean(r)}")
