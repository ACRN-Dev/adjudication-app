import json

with open('c:\\Automation\\Adjudication app\\scratch\\sample_participants.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    for v in p.get('visits', []):
        if 'evidence' in v:
            for k, rows in v['evidence'].items():
                for r in rows:
                    val = str(r.get('numeric_value') or r.get('raw_source_value') or r.get('value') or '')
                    if 'cephalic' in val.lower() or 'cervical' in val.lower() or 'amniotic' in val.lower() or 'foetal' in val.lower():
                        print(f"Subject: {p.get('subject_id')} Visit: {v.get('name')} -> {k} = {val}")
