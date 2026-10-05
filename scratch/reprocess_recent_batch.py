import sys
sys.path.insert(0, 'backend')

from database import Base, _create_engine_with_fallback, get_db
from models.canonical import Participant
from models.longitudinal import RTImportBatch, LongitudinalParticipant, VisitInstance, CanonicalObservation
from models.history import PatientHistoryField, PatientRiskSummary
from services.realtime_pipeline import process_batch
from sqlalchemy.orm import sessionmaker

eng, is_offline = _create_engine_with_fallback()
Session = sessionmaker(bind=eng)
db = Session()

# Find the most recent batch
b = db.query(RTImportBatch).order_by(RTImportBatch.uploaded_at.desc()).first()
print(f"Reprocessing batch: {b.id}, file: {b.filename}, source_path: {b.source_path}")

# Delete old observations, visit derivations, etc. for this batch to re-run cleanly
print("Clearing previous observations and fields for batch...")
p_ids = [p.id for p in db.query(LongitudinalParticipant).filter_by(source_batch_id=b.id).all()]
db.query(CanonicalObservation).filter_by(source_batch_id=b.id).delete()
db.query(VisitInstance).filter_by(source_batch_id=b.id).delete()
if p_ids:
    db.query(PatientRiskSummary).filter(PatientRiskSummary.participant_id.in_(p_ids)).delete(synchronize_session=False)
db.query(PatientHistoryField).filter_by(source_batch_id=b.id).delete()
# Reset batch status
b.status = "CHECKSUM_CALCULATED"
b.rows_processed = 0
db.commit()

print("Calling process_batch...")
process_batch(b.id)

print("Process batch completed!")
# Check results for participants
for p in db.query(LongitudinalParticipant).filter_by(source_batch_id=b.id).all():
    print(f"\nParticipant: {p.blinded_subject_id}")
    age_f = db.query(PatientHistoryField).filter_by(participant_id=p.id, field_key="age").first()
    print(f"  Age field: {age_f.value if age_f else 'None'}")
    
    # Check visits and GA
    for v in db.query(VisitInstance).filter_by(participant_id=p.id).order_by(VisitInstance.scheduled_visit_code).all():
        # count observations
        hr_obs = db.query(CanonicalObservation).filter_by(visit_id=v.id, canonical_variable="heart_rate").first()
        wt_obs = db.query(CanonicalObservation).filter_by(visit_id=v.id, canonical_variable="weight").first()
        bp_obs = db.query(CanonicalObservation).filter_by(visit_id=v.id, canonical_variable="bp_systolic").first()
        ga_d = v.gestational_age_days
        ga_str = f"{ga_d//7}w {ga_d%7}d" if ga_d else "None"
        print(f"  Visit {v.scheduled_visit_code}: GA_days={ga_d} ({ga_str}) | BP={bp_obs.raw_source_value if bp_obs else '-'} | HR={hr_obs.raw_source_value if hr_obs else '-'} | Wt={wt_obs.raw_source_value if wt_obs else '-'}")

db.close()
