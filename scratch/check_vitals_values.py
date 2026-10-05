import csv

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'

with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    
    # Check Age column for each subject
    subj_ages = {}
    vitals_with_val = []
    ga_with_val = []
    
    for row in reader:
        mrn = row.get("MRN") or ""
        scr = row.get("Screening #") or ""
        age_col = row.get("Age") or ""
        key = scr or mrn
        if age_col and key not in subj_ages:
            subj_ages[key] = age_col
            
        label = row.get("Field Label") or ""
        val = row.get("Data Value") or row.get("Data Input") or ""
        form = row.get("Form Title") or ""
        page = row.get("Page Title") or ""
        var_name = row.get("Export Variable Name") or ""
        
        if val:
            low = (label + " " + var_name + " " + page).lower()
            if any(k in low for k in ['heart', 'pulse', 'weight', 'temp', 'bp', 'systolic', 'diastolic']):
                vitals_with_val.append((key, form, page, label, var_name, val))
            if any(k in low for k in ['ega', 'gestat', 'ga_']):
                ga_with_val.append((key, form, page, label, var_name, val))

print("Subject Ages from 'Age' column:", subj_ages)
print(f"\nVitals with values ({len(vitals_with_val)} total):")
for v in vitals_with_val[:30]:
    print(f"Subj: {v[0]} | Form: {v[1]} | Page: {v[2]} | Label: {v[3]} | Var: {v[4]} | Val: {v[5]}")

print(f"\nGA with values ({len(ga_with_val)} total):")
for g in ga_with_val[:30]:
    print(f"Subj: {g[0]} | Form: {g[1]} | Page: {g[2]} | Label: {g[3]} | Var: {g[4]} | Val: {g[5]}")
