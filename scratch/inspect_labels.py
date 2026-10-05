import csv
import os

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'
if not os.path.exists(staging_path):
    print("Not found:", staging_path)
else:
    with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        # find header line
        header_line = None
        for i, line in enumerate(f):
            if "MRN" in line or "Screening #" in line or "Form Title" in line:
                header_line = i
                break
        print(f"Header line found at {header_line}")
        f.seek(0)
        for _ in range(header_line):
            f.readline()
        reader = csv.DictReader(f)
        print("Fields in CSV:", reader.fieldnames)
        
        # Collect sample fields
        interesting = []
        subjects = set()
        labels = set()
        for row in reader:
            mrn = row.get("MRN") or row.get("Screening #") or ""
            subjects.add(mrn)
            label = row.get("Field Label") or ""
            labels.add(label)
            val = row.get("Data Value") or row.get("Data Input") or ""
            form = row.get("Form Title") or ""
            page = row.get("Page Title") or ""
            
            # check for age, heart, weight, gestational
            lower = (label + " " + page + " " + form).lower()
            if any(k in lower for k in ['age', 'heart', 'pulse', 'weight', 'gestat', 'ega', 'ga']):
                interesting.append((mrn, form, page, label, val))
                
        print(f"Total distinct subjects: {len(subjects)}")
        print(f"Distinct subjects: {list(subjects)[:5]}")
        print(f"\nInteresting rows (total {len(interesting)}):")
        # Print a sample of 30 interesting rows
        for row in interesting[:40]:
            print(f"Subj: {row[0][:15]} | Form: {row[1][:25]} | Page: {row[2][:20]} | Label: {row[3][:35]} | Val: {row[4]}")
