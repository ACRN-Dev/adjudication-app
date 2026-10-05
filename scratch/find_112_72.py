import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

query = """
SELECT p.blinded_subject_id, v.scheduled_visit_code, v.form_title, o.canonical_variable, o.raw_source_value
FROM canonical_observations o
JOIN visit_instances v ON o.visit_id = v.id
JOIN longitudinal_participants p ON o.participant_id = p.id
WHERE o.raw_source_value IN ('112', '72')
"""
for r in c.execute(query):
    print(r)
