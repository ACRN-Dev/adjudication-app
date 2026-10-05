import sqlite3

conn = sqlite3.connect('backend/acrn_demo.db')
c = conn.cursor()
c.execute("SELECT id, blinded_subject_id FROM longitudinal_participants")
all_pts = c.fetchall()

performed_no_date = []
not_performed = []
normal_visits = []

for pid, bsid in all_pts:
    c.execute("""
        SELECT scheduled_visit_code, visit_sequence, visit_datetime, gestational_age_days, id 
        FROM visit_instances 
        WHERE participant_id = ? AND scheduled_visit_code IN ('V01','V02','V03','V04','V05','V06') 
        ORDER BY visit_sequence
    """, (pid,))
    visits = c.fetchall()
    for vcode, vseq, vdt, ga, vid in visits:
        c.execute("SELECT canonical_variable, raw_source_value, observation_datetime, source_field_label FROM canonical_observations WHERE visit_id = ?", (vid,))
        obs = c.fetchall()
        
        # Check if reason for not performing visit exists
        reasons = [o for o in obs if 'not performing' in (o[3] or '').lower() or o[1] in ('Delivered', 'Missed visit', 'Withdrew', 'Lost to follow-up')]
        
        # Check if other clinical data exists
        clinical_obs = [o for o in obs if o[0] not in ('visit_date', 'health_status', 'health_status_description') and 'not performing' not in (o[3] or '').lower() and o[1] not in ('Delivered', 'Missed visit')]
        
        if reasons and not clinical_obs:
            reason_str = ", ".join([f"{o[3]}: {o[1]}" for o in reasons])
            not_performed.append((bsid, vcode, reason_str))
        elif len(obs) == 0:
            not_performed.append((bsid, vcode, "No observations recorded"))
        elif vdt is None:
            performed_no_date.append((bsid, vcode, len(obs), [o[0] for o in obs[:5]]))
        else:
            normal_visits.append((bsid, vcode, str(vdt), len(obs)))

print(f"Total participants: {len(all_pts)}")
print(f"Total performed visits with date: {len(normal_visits)}")
print(f"Total performed visits WITHOUT date: {len(performed_no_date)}")
if performed_no_date:
    print("Performed visits without date:")
    for item in performed_no_date:
        print("  ", item)
print(f"\nTotal visits not performed / missed: {len(not_performed)}")
for item in not_performed[:15]:
    print("  ", item)
