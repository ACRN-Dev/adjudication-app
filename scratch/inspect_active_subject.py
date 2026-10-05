import sqlite3
import csv
from cryptography.fernet import Fernet
import os

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants WHERE blinded_subject_id = 'ACRN-655667EDA079'")
p = c.fetchone()
print("Participant:", p)

c.execute("SELECT protected_mrn, screening_number FROM restricted_identity_crosswalk WHERE participant_id = ?", (p[0],))
crosswalk = c.fetchone()
print("Crosswalk encrypted:", crosswalk)

# Look in backend/.rt-staging/940f9f4f-ef15-4657-a383-a1a3257b8b82.csv to find which subject had SBP 112, DBP 72 in Visit 2
staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'
matched_subjid = None
with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("Form Title") == "Visit 2" and (row.get("Data Value") == "112" or row.get("Data Input") == "112"):
            matched_subjid = row.get("Screening #") or row.get("MRN")
            print(f"Matched subject ID in CSV: {matched_subjid}")
            print(f"Age in CSV: {row.get('Age')}")
            break

# Now dump all rows for this matched subject
rows_for_subj = []
with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for row in reader:
        sid = row.get("Screening #") or row.get("MRN")
        if sid == matched_subjid:
            rows_for_subj.append(row)

print(f"\nTotal rows for {matched_subjid}: {len(rows_for_subj)}")
print(f"Age column across rows: {set(r.get('Age') for r in rows_for_subj)}")

# Print all vitals and GA rows for this subject
print("\n--- All Vitals & GA for this subject ---")
for r in rows_for_subj:
    label = r.get("Field Label") or ""
    val = r.get("Data Value") or r.get("Data Input") or ""
    form = r.get("Form Title") or ""
    page = r.get("Page Title") or ""
    low = (label + " " + page).lower()
    if val and any(k in low for k in ['systolic', 'diastolic', 'heart', 'pulse', 'weight', 'temperature', 'protein', 'gestational', 'ega', 'height', 'bmi']):
        print(f"[{form}] {page} -> {label} = {val!r}")
