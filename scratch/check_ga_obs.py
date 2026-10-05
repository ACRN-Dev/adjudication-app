import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()
c.execute("""
    SELECT v.scheduled_visit_code, v.visit_sequence, v.gestational_age_days, o.canonical_variable, o.raw_source_value 
    FROM visit_instances v 
    LEFT JOIN canonical_observations o ON o.visit_id = v.id AND (o.canonical_variable LIKE '%ega%' OR o.canonical_variable LIKE '%ga%')
    WHERE v.scheduled_visit_code IN ('V01','V02','V03','V04','V05','V06')
    LIMIT 30
""")
for row in c.fetchall():
    print(row)
