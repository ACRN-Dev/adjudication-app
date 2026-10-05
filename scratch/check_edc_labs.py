import glob
import csv

edc_files = glob.glob("EDC/*.csv")
lab_tests = set()
questions = set()
matching_rows = []

for f in edc_files:
    print(f"Reading {f}...")
    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
        line = fp.readline()
        while line and not line.startswith("Study Version"):
            line = fp.readline()
        if not line:
            continue
        reader = csv.DictReader([line] + fp.readlines())
        for i, row in enumerate(reader):
            q = (row.get("Question Label") or "").strip()
            v = (row.get("Value") or "").strip()
            if q in ["Lab Test", "Test Name", "Analyte", "Parameter"]:
                lab_tests.add(v)
            if any(term in q.lower() for term in ["lymph", "neut", "hematocrit", "hct", "alc", "anc"]):
                questions.add((q, v, row.get("Form Title", "")))
            if any(term in v.lower() for term in ["lymph", "neut", "hematocrit", "hct", "alc", "anc"]):
                matching_rows.append((row.get("Subject Number") or row.get("Subject ID"), row.get("Form Title"), q, v))

print("\n--- Unique Lab Tests Found in EDC ---")
for t in sorted(lab_tests):
    print(t)

print("\n--- Questions matching keywords ---")
for q in questions:
    print(q)

print(f"\n--- Matching rows count: {len(matching_rows)} ---")
for r in matching_rows[:20]:
    print(r)
