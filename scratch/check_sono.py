import json

with open('c:\\Automation\\Adjudication app\\edc_mapping_catalog.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    if 'sono' in str(m.get('form')).lower() or 'ultrasound' in str(m.get('form')).lower():
        print(f"{m.get('target_field')} <- {m.get('source_field')} (Form: {m.get('form')})")
