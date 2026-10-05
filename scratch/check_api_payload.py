import sys
sys.path.insert(0, 'backend')

from database import _create_engine_with_fallback
from models.longitudinal import LongitudinalParticipant
from api.realtime import pjson
from sqlalchemy.orm import sessionmaker

eng, is_offline = _create_engine_with_fallback()
Session = sessionmaker(bind=eng)
db = Session()

p = db.query(LongitudinalParticipant).filter_by(blinded_subject_id="ACRN-655667EDA079").first()
if p:
    data = pjson(p, db)
    print("Patient data from pjson:")
    print("  Subject:", data.get("subject_id"))
    print("  Age:", data.get("age"))
    print("  Visits count:", data.get("canonical_visit_count"))
db.close()
