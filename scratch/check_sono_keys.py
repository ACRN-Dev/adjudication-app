import json

with open('c:\\Automation\\Adjudication app\\scratch\\sample_participants.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    for v in p.get('visits', []):
        if 'evidence' in v:
            for k in v['evidence'].keys():
                if 'sono' in k.lower() or 'ultras' in k.lower() or 'fetal' in k.lower() or 'cervix' in k.lower() or 'ega' in k.lower() or 'amn' in k.lower() or 'placenta' in k.lower() or 'efw' in k.lower() or 'fhr' in k.lower():
                    print(f"Key: {k}")
