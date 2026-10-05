import os
import glob
import pandas as pd

# Let's inspect columns of CSV files in rt/
for f in glob.glob("rt/*.csv"):
    print(f"=== {f} ===")
    try:
        # read header
        df = pd.read_csv(f, nrows=5)
        print("Columns count:", len(df.columns))
        # Search for lymphocyte, neutrophil, hematocrit, alc, anc, hct, etc.
        matches = [c for c in df.columns if any(k in c.lower() for k in ['lymph', 'neut', 'hemat', 'hct', 'alc', 'anc', 'wbc', 'rbc', 'platelet', 'protein', 'creatinine'])]
        print("Matching columns:", matches)
        # print non-null values for first 5 rows of matches
        if matches:
            print(df[matches].head(3))
    except Exception as e:
        print(f"Error reading {f}: {e}")

# Let's check EDC files
for f in glob.glob("EDC/*.csv")[:2]:
    print(f"=== {f} ===")
    try:
        df = pd.read_csv(f, nrows=5)
        matches = [c for c in df.columns if any(k in c.lower() for k in ['lymph', 'neut', 'hemat', 'hct', 'alc', 'anc'])]
        print("Matching columns:", matches)
    except Exception as e:
        print(f"Error reading {f}: {e}")
