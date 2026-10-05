import csv

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'
with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    seen = set()
    for row in reader:
        label = row.get("Field Label") or ""
        page = row.get("Page Title") or ""
        low = label.lower()
        if any(w in low for w in ['systolic', 'diastolic', 'weight', 'heart', 'pulse']):
            pair = (page, label)
            if pair not in seen:
                seen.add(pair)
                val = row.get("Data Value") or row.get("Data Input") or ""
                print(f"Page: {page} | Label: {label} | Sample Val: {val}")
