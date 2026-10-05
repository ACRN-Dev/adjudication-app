import csv

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'

with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    
    for row in reader:
        mrn = row.get("MRN") or row.get("Screening #") or ""
        form = row.get("Form Title") or ""
        page = row.get("Page Title") or ""
        label = row.get("Field Label") or ""
        var = row.get("Export Variable Name") or ""
        val = row.get("Data Value") or row.get("Data Input") or ""
        
        all_text = f"{form} | {page} | {label} | {var}".lower()
        if any(k in all_text for k in ["gestat", "ega", "weeks", "days", "ultrasound"]) and val:
            # only print if has value
            if any(k in all_text for k in ["gestat", "ega", "uss"]):
                print(f"[{mrn}] {form} -> Page: {page} | Label: {label} | Var: {var} | Val: {val}")
