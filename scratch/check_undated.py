import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()

c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants WHERE blinded_subject_id LIKE '%9%' OR id = 9")
pts = c.fetchall()
c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants")
all_pts = c.fetchall()
print(f"Checking {len(all_pts)} participants for visits with visit_datetime=None:")
for pid, bsid in all_pts:
    c.execute("SELECT scheduled_visit_code, visit_sequence, visit_datetime, gestational_age_days, form_title FROM visit_instances WHERE participant_id = ? AND scheduled_visit_code IN ('V01','V02','V03','V04','V05','V06') ORDER BY visit_sequence", (pid,))
    visits = c.fetchall()
    undated = [v for v in visits if v[2] is None]
    if undated:
        print(f"\nParticipant {bsid}:")
        for vcode, vseq, vdt, ga, ftitle in visits:
            c.execute("SELECT canonical_variable, raw_source_value, observation_datetime, source_field_label FROM canonical_observations WHERE visit_id IN (SELECT id FROM visit_instances WHERE participant_id = ? AND scheduled_visit_code = ?)", (pid, vcode))
            obs = c.fetchall()
            print(f"  {vcode}: dt={vdt}, ga={ga}, obs_count={len(obs)}")
            for o in obs:
                print(f"    -> {o}")
