import json

with open('c:\\Automation\\Adjudication app\\scratch\\sample_participants.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    for v in p.get('visits', []):
        if 'observations' in v:
            for obs in v['observations']:
                val = str(obs.get('value', '')).lower()
                if 'cephalic' in val or 'cervical' in val or '15 weeks' in val:
                    print(f"Subject: {p.get('subject_id')} -> {obs.get('source_field')} = {obs.get('value')}")
