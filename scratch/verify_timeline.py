import sys
sys.path.insert(0, 'backend')

from database import _create_engine_with_fallback
from models.longitudinal import LongitudinalParticipant
from api.realtime import timeline
from sqlalchemy.orm import sessionmaker

eng, is_offline = _create_engine_with_fallback()
Session = sessionmaker(bind=eng)
db = Session()

p = db.query(LongitudinalParticipant).filter_by(blinded_subject_id="ACRN-655667EDA079").first()
if p:
    tl = timeline(p, db)
    print("Timeline for ACRN-655667EDA079:")
    print("  Age:", tl.get("age"))
    print("  Risk summary:", tl.get("risk_summary"))
    print("  Visits count:", len(tl.get("visits", [])))
    for v in tl.get("visits", []):
        ev = v.get("evidence", {})
        print(f"\n  Visit {v.get('name')}:")
        print(f"    GA: {v.get('ga')} (days: {v.get('ga_days')})")
        print(f"    BP systolic evidence: {[x['value'] for x in ev.get('bp_systolic', [])]}")
        print(f"    BP diastolic evidence: {[x['value'] for x in ev.get('bp_diastolic', [])]}")
        print(f"    Heart rate evidence: {[x['value'] for x in ev.get('heart_rate', [])]}")
        print(f"    Weight evidence: {[x['value'] for x in ev.get('weight', [])]}")
db.close()
