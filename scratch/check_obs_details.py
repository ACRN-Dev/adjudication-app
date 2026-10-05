import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

c.execute("""
SELECT v.scheduled_visit_code, o.canonical_variable, o.raw_source_value, o.numeric_value, o.source_field_label
FROM canonical_observations o
JOIN visit_instances v ON o.visit_id = v.id
JOIN longitudinal_participants p ON o.participant_id = p.id
WHERE p.blinded_subject_id = 'ACRN-655667EDA079' AND v.scheduled_visit_code IN ('V02', 'V03', 'V04', 'V01', 'V05', 'V06')
""")
rows = c.fetchall()
print(f"Total observations for ACRN-655667EDA079: {len(rows)}")
for r in rows:
    if any(k in r[1] for k in ['bp', 'heart', 'pulse', 'weight', 'temp', 'ega', 'protein', 'upcr']):
        print(f"[{r[0]}] {r[1]} -> raw={r[2]!r}, num={r[3]}, label={r[4]!r}")
