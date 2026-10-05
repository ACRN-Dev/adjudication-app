import csv

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'
with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        mrn = row.get("MRN") or row.get("Screening #") or ""
        if mrn in ("6947", "ZWE001-0018"):
            form = row.get("Form Title") or ""
            if "Visit 2" in form:
                label = row.get("Field Label") or ""
                val = row.get("Data Value") or row.get("Data Input") or ""
                if val:
                    low = label.lower()
                    if any(k in low for k in ['blood', 'pressure', 'bp', 'systolic', 'diastolic', '112', '72']):
                        print(f"Row {i} | Form: {form} | Page: {row.get('Page Title')} | Label: {label} | Val: {val}")
