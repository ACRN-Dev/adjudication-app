import csv
import sys
sys.path.insert(0, 'backend')
from services.realtime_mapping import map_variable, classify

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'

with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        label = row.get("Field Label") or ""
        if "weight" in label.lower() or "pulse" in label.lower() or "heart" in label.lower():
            mapped = map_variable(row)
            cat = classify(row)
            val = row.get("Data Value") or row.get("Data Input") or ""
            print(f"Row {i}: Label='{label}' | Page='{row.get('Page Title')}' | Val='{val}' -> Mapped: {mapped}, Cat: {cat}")
