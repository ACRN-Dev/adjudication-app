import sqlite3
import json

c = sqlite3.connect('c:/Automation/Adjudication app/backend/acrn_demo.db')
rows = c.execute("SELECT participant_id, visit_id, canonical_variable FROM canonical_observations WHERE canonical_variable LIKE '%lymphocyte%'").fetchall()
print("ROWS: ", rows)
