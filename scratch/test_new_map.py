import csv
import re
import sys
sys.path.insert(0, 'backend')
from services.realtime_mapping import RULES, NON_RESULT_PATTERNS, DIRECT_ALIASES, norm

def new_map_variable(row):
    field_text = norm(row.get("Field Label"))
    if any(pattern.search(field_text) for pattern in NON_RESULT_PATTERNS):
        return None
    export_name = norm(row.get("Export Variable Name")).replace(" ", "_")
    if export_name in DIRECT_ALIASES:
        return DIRECT_ALIASES[export_name]
    text = " | ".join(norm(row.get(k)) for k in ("Page Title", "Field Label", "Export Variable Name"))
    for canonical, patterns in RULES:
        if any(p.search(text) or p.search(field_text) or (export_name and p.search(export_name)) for p in patterns):
            return canonical
    return None

staging_path = r'backend\.rt-staging\940f9f4f-ef15-4657-a383-a1a3257b8b82.csv'
counts = {}
with open(staging_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
    for _ in range(7):
        f.readline()
    reader = csv.DictReader(f)
    for row in reader:
        c = new_map_variable(row)
        if c:
            counts[c] = counts.get(c, 0) + 1

print("New mapped counts:")
for k in sorted(counts.keys()):
    if any(x in k for x in ['heart', 'weight', 'pulse', 'temp', 'bp', 'age']):
        print(f"  {k}: {counts[k]}")
