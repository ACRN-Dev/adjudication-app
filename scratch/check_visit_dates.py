import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()
c.execute("PRAGMA table_info(longitudinal_participants)")
print("longitudinal_participants columns:", [r[1] for r in c.fetchall()])

c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants")
pts = c.fetchall()
print(f"Total participants: {len(pts)}")
for pid, bsid in pts[:5]:
    print(f"\n--- Participant {bsid} (id={pid}) ---")
    c.execute("SELECT id, scheduled_visit_code, visit_sequence, visit_datetime, gestational_age_days, form_title FROM visit_instances WHERE participant_id = ? ORDER BY visit_sequence", (pid,))
    visits = c.fetchall()
    for vid, vcode, vseq, vdt, ga, ftitle in visits:
        c.execute("SELECT MIN(observation_datetime), MAX(observation_datetime), COUNT(*) FROM canonical_observations WHERE visit_id = ?", (vid,))
        min_dt, max_dt, count = c.fetchone()
        c.execute("SELECT canonical_variable, raw_source_value, observation_datetime FROM canonical_observations WHERE visit_id = ? AND (canonical_variable LIKE '%date%' OR canonical_variable LIKE '%visit%') LIMIT 5", (vid,))
        date_obs = c.fetchall()
        print(f"  Visit {vcode} (seq={vseq}): visit_datetime={vdt}, obs_count={count}, min_obs_dt={min_dt}, max_obs_dt={max_dt}")
        if count > 0 and vdt is None:
            c.execute("SELECT canonical_variable, raw_source_value, observation_datetime, source_field_label FROM canonical_observations WHERE visit_id = ? LIMIT 5", (vid,))
            print(f"    Sample obs: {c.fetchall()}")
        elif count == 0:
            print("    [NO OBSERVATIONS FOR THIS VISIT]")
