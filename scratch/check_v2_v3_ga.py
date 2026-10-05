import csv

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'

with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        mrn = row.get("MRN") or row.get("Screening #") or ""
        form = row.get("Form Title") or ""
        label = row.get("Field Label") or ""
        var = row.get("Export Variable Name") or ""
        val = row.get("Data Value") or row.get("Data Input") or ""
        if mrn == "6947" and ("Visit 2" in form or "Visit 3" in form) and "gestational" in label.lower():
            print(f"Row {i}: Form={form} | Page={row.get('Page Title')} | Label={label!r} | Var={var!r} | Val={val!r} | Audit={row.get('Audit Trails')!r}")
