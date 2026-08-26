"""Configurable per-site/per-lab Normal vs. Abnormal flagging for lab analytes.

Resolution order for a given (site_code, analyte):
  1. Active LabReferenceRange row scoped to that exact site_code + analyte
  2. Active LabReferenceRange row with site_code=NULL (global override) for that analyte
  3. Built-in clinical default range (DEFAULT_RANGES)
  4. No range known -> flag is UNKNOWN, never silently treated as Normal
"""
from sqlalchemy.orm import Session

from models.longitudinal import CanonicalObservation, LabReferenceRange

# Built-in adult reference ranges used only when no configured override exists.
DEFAULT_RANGES = {
    "PLATELETS":        {"low": 150, "high": 450, "unit": "10^3/uL"},
    "CREATININE":       {"low": 0.5, "high": 1.1, "unit": "mg/dL"},
    "AST":              {"low": 5, "high": 40, "unit": "U/L"},
    "ALT":              {"low": 7, "high": 56, "unit": "U/L"},
    "LDH":              {"low": 140, "high": 280, "unit": "U/L"},
    "UPCR":             {"low": 0, "high": 0.3, "unit": "mg/mg"},
}

LAB_ANALYTES = tuple(DEFAULT_RANGES.keys())


def _resolve_range(db: Session, site_code: str | None, analyte: str) -> dict | None:
    if site_code:
        row = (
            db.query(LabReferenceRange)
            .filter_by(analyte=analyte, site_code=site_code, is_active=True)
            .first()
        )
        if row:
            return {"low": row.low, "high": row.high, "unit": row.unit, "source": "SITE_OVERRIDE"}
    global_row = (
        db.query(LabReferenceRange)
        .filter_by(analyte=analyte, site_code=None, is_active=True)
        .first()
    )
    if global_row:
        return {"low": global_row.low, "high": global_row.high, "unit": global_row.unit, "source": "CONFIGURED_DEFAULT"}
    default = DEFAULT_RANGES.get(analyte)
    if default:
        return {**default, "source": "BUILTIN_DEFAULT"}
    return None


def evaluate_participant_labs(db: Session, participant) -> dict:
    """Return {"status": NORMAL|ABNORMAL|NO_DATA, "abnormal_count": n, "flags": [...]}."""
    flags = []
    for analyte in LAB_ANALYTES:
        obs = (
            db.query(CanonicalObservation)
            .filter_by(participant_id=participant.id, canonical_variable=analyte)
            .filter(CanonicalObservation.numeric_value.isnot(None))
            .order_by(CanonicalObservation.observation_datetime.desc().nullslast())
            .first()
        )
        if not obs:
            continue
        range_ = _resolve_range(db, participant.site_code, analyte)
        if not range_:
            flags.append({"analyte": analyte, "value": obs.numeric_value, "unit": obs.unit, "result": "UNKNOWN", "reference": None})
            continue
        low, high = range_.get("low"), range_.get("high")
        is_abnormal = (low is not None and obs.numeric_value < low) or (high is not None and obs.numeric_value > high)
        flags.append({
            "analyte": analyte,
            "value": obs.numeric_value,
            "unit": obs.unit or range_.get("unit"),
            "result": "ABNORMAL" if is_abnormal else "NORMAL",
            "reference": {"low": low, "high": high, "unit": range_.get("unit"), "source": range_.get("source")},
        })
    abnormal_count = sum(1 for f in flags if f["result"] == "ABNORMAL")
    if not flags:
        status = "NO_DATA"
    elif abnormal_count:
        status = "ABNORMAL"
    else:
        status = "NORMAL"
    return {"status": status, "abnormal_count": abnormal_count, "flags": flags}
