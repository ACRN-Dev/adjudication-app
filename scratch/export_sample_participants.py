import sqlite3, json

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants")
pts = c.fetchall()

result = []
for pid, bsid in pts:
    c.execute("""
      SELECT id, scheduled_visit_code, visit_sequence, visit_datetime, gestational_age_days, form_title 
      FROM visit_instances 
      WHERE participant_id = ? AND scheduled_visit_code IN ('V01','V02','V03','V04','V05','V06')
      ORDER BY visit_sequence
    """, (pid,))
    visits = c.fetchall()
    v_list = []
    for vid, vcode, vseq, vdt, ga, ftitle in visits:
        c.execute("SELECT canonical_variable, raw_source_value, observation_datetime, source_field_label FROM canonical_observations WHERE visit_id = ?", (vid,))
        obs = c.fetchall()
        evidence = {}
        for o in obs:
            evidence.setdefault(o[0], []).append({
                "value": o[1],
                "raw_source_value": o[1],
                "observed_at": o[2],
                "source_field_label": o[3]
            })
        v_list.append({
            "id": vid,
            "visit_number": vseq,
            "scheduled_visit_code": vcode,
            "name": vcode,
            "date": vdt,
            "gestational_age_days": ga,
            "evidence": evidence,
            "observations": [{"canonical_variable": o[0], "raw_source_value": o[1], "observation_datetime": o[2], "source_field_label": o[3]} for o in obs]
        })
    result.append({"id": bsid, "visits": v_list})

with open("scratch/sample_participants.json", "w") as f:
    json.dump(result, f, indent=2)
print("Dumped", len(result), "participants to scratch/sample_participants.json")
