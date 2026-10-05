import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

print("--- VisitInstance rows for batch ---")
for r in c.execute("SELECT id, participant_id, form_title, scheduled_visit_code, gestational_age_days, visit_datetime FROM visit_instances LIMIT 25"):
    print(r)

print("\n--- LongitudinalParticipant rows ---")
for r in c.execute("SELECT id, blinded_subject_id, onset_classification, maximum_severity FROM longitudinal_participants"):
    print(r)
