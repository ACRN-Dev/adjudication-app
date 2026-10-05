import sqlite3

conn = sqlite3.connect("backend/acrn_demo.db")
c = conn.cursor()

# Get participants
participants = c.execute("SELECT id, blinded_subject_id, study FROM longitudinal_participants").fetchall()
print(f"Total participants in acrn_demo.db: {len(participants)}")
for p in participants[:10]:
    print(p)

# Check distinct canonical_variables in canonical_observations
canonical_vars = c.execute("SELECT canonical_variable, count(*) FROM canonical_observations GROUP BY canonical_variable ORDER BY count(*) DESC").fetchall()
print("\nCanonical variables and counts in canonical_observations:")
for cv, count in canonical_vars:
    print(f"  {cv}: {count}")

# Check if there are any observations for alc, anc, haematocrit, lymphocyte, neutrophil, hematocrit
matches = c.execute("SELECT DISTINCT canonical_variable FROM canonical_observations WHERE canonical_variable LIKE '%lymph%' OR canonical_variable LIKE '%neut%' OR canonical_variable LIKE '%alc%' OR canonical_variable LIKE '%anc%' OR canonical_variable LIKE '%hemat%' OR canonical_variable LIKE '%haemat%'").fetchall()
print("\nMatching variables in canonical_observations:", matches)

# Check source_batches
batches = c.execute("SELECT id, filename, source_system, status, row_count, participant_count, imported_at FROM monitor_import_batches").fetchall()
print("\nMonitor import batches:")
for b in batches:
    print(b)
