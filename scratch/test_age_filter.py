import re

def test_age_rule(label):
    norm = label.strip().lower()
    # If it has gestational, it's NOT maternal age
    if 'gestat' in norm or 'uss' in norm or 'delivery' in norm or 'scan' in norm:
        return False
    return bool(re.search(r'\bage\b', norm))

labels = [
    "Age",
    "Current Gestational Age  (calculated using first USS)",
    "Gestational Age on first USS",
    "Gestational age at delivery",
    "Gestational age on scan",
    "Patient age",
    "Age at enrollment"
]
for l in labels:
    print(f"'{l}' -> is_age: {test_age_rule(l)}")
