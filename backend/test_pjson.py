import traceback
from database import SessionLocal
from models.longitudinal import LongitudinalParticipant
from api.realtime import pjson

db = SessionLocal()
try:
    pts = db.query(LongitudinalParticipant).all()
    print(f"Found {len(pts)} participants in DB")
    for p in pts[:5]:
        res = pjson(p)
        print("PJSON OK:", res["subject_id"])
except Exception as e:
    traceback.print_exc()
finally:
    db.close()
