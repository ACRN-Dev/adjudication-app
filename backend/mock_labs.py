import sqlite3
import uuid

c = sqlite3.connect('acrn_demo.db')
# Get one participant and visit
row = c.execute('SELECT participant_id, visit_id, source_batch_id, observation_datetime FROM canonical_observations WHERE canonical_variable="wbc" LIMIT 1').fetchone()
participant_id, visit_id, source_batch_id, observation_datetime = row

# Insert the missing labs
def insert_lab(var_name, val):
    c.execute(
        '''INSERT INTO canonical_observations 
           (id, participant_id, visit_id, source_batch_id, canonical_variable, raw_source_value, numeric_value, observation_datetime) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (str(uuid.uuid4()), participant_id, visit_id, source_batch_id, var_name, str(val), val, observation_datetime)
    )

insert_lab('absolute_lymphocyte_count', 1.5)
insert_lab('absolute_neutrophil_count', 4.2)
insert_lab('hematocrit', 38.5)

c.commit()
print("Successfully inserted mock labs")
