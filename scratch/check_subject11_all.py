import json

with open('c:\\Automation\\Adjudication app\\scratch\\sample_participants.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    if '11' in p.get('subject_id', ''):
        print(f"Subject: {p.get('subject_id')}")
        for v in p.get('visits', []):
            print(f"  Visit {v.get('visit_number')} ({v.get('name')})")
            if 'evidence' in v:
                for k, rows in v['evidence'].items():
                    for r in rows:
                        val = r.get('numeric_value') or r.get('raw_source_value') or r.get('value')
                        if val:
                            print(f"    {k} = {val}")
