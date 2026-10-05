import sqlite3
import pandas as pd
import os
import glob

# Inspect the staging file from rt_import_batches
conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()
c.execute("SELECT id, filename, source_path FROM rt_import_batches ORDER BY uploaded_at DESC LIMIT 1")
batch = c.fetchone()
print("Batch:", batch)

staging_path = batch[2]
if os.path.exists(staging_path):
    print("Staging path exists:", staging_path)
    df = pd.read_csv(staging_path, nrows=50)
    print("CSV Columns:", df.columns.tolist())
    print("\nSample rows:")
    print(df.head(5).to_string())
else:
    print("Staging path not found, searching in backend/.rt-staging/")
    files = glob.glob("backend/.rt-staging/*.csv")
    for f in sorted(files, key=os.path.getmtime, reverse=True)[:3]:
        print("Recent staging file:", f, os.path.getsize(f))
        df = pd.read_csv(f, nrows=10)
        print("Columns:", df.columns.tolist()[:20])

# Also check patient_history_fields in db
print("\n--- patient_history_fields distinct field names ---")
c.execute("SELECT DISTINCT field_name FROM patient_history_fields")
fields = [r[0] for r in c.fetchall()]
print(fields)

# Check canonical_observations distinct observation_names or codes
print("\n--- canonical_observations distinct names ---")
c.execute("SELECT DISTINCT observation_name FROM canonical_observations LIMIT 50")
obs = [r[0] for r in c.fetchall()]
print(obs)
