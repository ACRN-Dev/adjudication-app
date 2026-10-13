import json
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from database import SessionLocal  # noqa: E402
from models.longitudinal import LongitudinalParticipant, RTImportBatch  # noqa: E402
from api.realtime import loaded, timeline  # noqa: E402


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


db = SessionLocal()
try:
    batch = db.query(RTImportBatch).order_by(RTImportBatch.uploaded_at.desc()).first()
    if batch is None:
        raise RuntimeError("No RealTime import batch is available")

    participant_rows = (
        db.query(LongitudinalParticipant)
        .filter_by(source_batch_id=batch.id)
        .order_by(LongitudinalParticipant.created_at)
        .all()
    )
    cases = []
    for participant_row in participant_rows:
        participant = loaded(db, participant_row.id)
        cases.append(timeline(participant, db))

    payload = {
        "batch": {
            "id": str(batch.id),
            "filename": batch.filename,
            "uploaded_at": batch.uploaded_at,
            "mapping_version": batch.mapping_version,
            "row_count": batch.row_count,
            "participant_count": batch.participant_count,
            "visit_count": batch.visit_count,
            "status": batch.status,
        },
        "cases": cases,
    }
    output = ROOT / "scratch" / "latest_blinded_batch.json"
    output.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")
    print(f"Exported {len(cases)} blinded cases to {output}")
finally:
    db.close()
