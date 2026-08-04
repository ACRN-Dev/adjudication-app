"""
Clinical Derivation API — POST /api/derive/{subject_id}
========================================================
Runs the original derivation engine (ISSHP-2021) PLUS the new
DV-01 through DV-30 engine (PROTECT-DV-2026.08) and returns both.

The dv_bundle in the response gives the comprehensive gate-ready result
used by the frontend gate-status panel and DV-27 certainty enforcement.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db, DB_OFFLINE
from models.canonical import Participant, CanonicalField, DerivationResult
from services.derivation_engine import run_full_derivation, CriterionResult

# Import DV engine if available
try:
    from services.dv_engine import run_dv_engine
    DV_ENGINE_AVAILABLE = True
except ImportError:
    DV_ENGINE_AVAILABLE = False

router = APIRouter()


def _safe_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _flag(v):
    return str(v or '').lower() in ('true', 'yes', '1', 'aedf', 'redf', 'abnormal')


@router.post("/{subject_id}")
def derive_criteria(subject_id: str, db: Session = Depends(get_db)):
    if DB_OFFLINE:
        return {
            "subject_id": subject_id,
            "status": "offline",
            "message": "Database unavailable. Use /api/derive/inline for derivation without a database connection.",
            "criteria": [],
            "dv_bundle": None,
            "derived_at": datetime.utcnow().isoformat(),
        }

    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    # Build field lookup from canonical fields (excluding blinded fields)
    fields = {
        f.canonical_field: f.canonical_value
        for f in participant.canonical_fields
        if not f.is_blinded
    }

    # --- Reconstruct repeated BP observations ---
    # Each BP visit is stored as a group of canonical fields with a visit suffix
    # e.g. SBP_1, DBP_1, EVENT_DT_1, GA_EVENT_1, SBP_2, DBP_2, ...
    bp_readings = []
    visit_indices = set()
    for key in fields:
        for prefix in ('SBP_', 'DBP_'):
            if key.startswith(prefix):
                try:
                    idx = int(key.split('_')[-1])
                    visit_indices.add(idx)
                except ValueError:
                    pass

    for idx in sorted(visit_indices):
        sbp = _safe_float(fields.get(f'SBP_{idx}'))
        dbp = _safe_float(fields.get(f'DBP_{idx}'))
        if sbp is not None and dbp is not None:
            bp_readings.append({
                'sbp': sbp,
                'dbp': dbp,
                'date': fields.get(f'EVENT_DT_{idx}'),
                'ga': fields.get(f'GA_EVENT_{idx}'),
                'source': fields.get(f'BP_SOURCE_{idx}', 'EDC'),
                'severe': (sbp >= 160 or dbp >= 110),
            })

    # Fallback: single SBP/DBP fields
    if not bp_readings:
        sbp = _safe_float(fields.get('SBP'))
        dbp = _safe_float(fields.get('DBP'))
        if sbp is not None and dbp is not None:
            bp_readings.append({
                'sbp': sbp, 'dbp': dbp,
                'date': fields.get('EVENT_DT'),
                'ga': fields.get('GA_EVENT'),
                'source': 'EDC',
                'severe': (sbp >= 160 or dbp >= 110),
            })

    # Build unified case_data dict
    case_data = {
        'subject_id': subject_id,
        'bp_readings': bp_readings,
        'bpLog': bp_readings,

        # Proteinuria — support both UPCR and UPCR_MGMMOL
        'upcr': _safe_float(fields.get('UPCR')),
        'dipstick_raw': fields.get('DIPSTICK'),
        'prot_24h_mg': _safe_float(fields.get('PROT_24H')),

        # Haematology
        'platelet_count': _safe_float(fields.get('PLATELET_COUNT') or fields.get('PLATELETS')),

        # Renal
        'creatinine_raw': fields.get('CREATININE'),
        'creatinine_unit': fields.get('CREATININE_UNIT', 'mg/dL'),
        'baseline_creatinine': _safe_float(fields.get('CREATININE_BASELINE')),

        # Hepatic
        'ast': _safe_float(fields.get('AST')),
        'alt': _safe_float(fields.get('ALT')),
        'ast_uln': _safe_float(fields.get('AST_ULN')) or 40.0,
        'alt_uln': _safe_float(fields.get('ALT_ULN')) or 35.0,
        'ldh': _safe_float(fields.get('LDH')),

        # Fetal
        'efw_centile': _safe_float(fields.get('EFW_CENTILE')),
        'efw_grams': _safe_float(fields.get('EFW_GRAMS')),
        'ua_aedf': _flag(fields.get('UA_AEDF')),
        'ua_redf': _flag(fields.get('UA_REDF')),
        'abruption': _flag(fields.get('ABRUPTION')),
        'iufd': _flag(fields.get('IUFD')),

        # Gestational age
        'ga_at_first_criterion': fields.get('GA_AT_EVENT') or fields.get('GA_EVENT'),
        'gaAtEvent': fields.get('GA_EVENT'),

        # Delivery
        'delivery_date': fields.get('DELIVERY_DATE'),
        'ga_at_delivery': fields.get('GA_DELIVERY'),
        'entered_ga_delivery': fields.get('GA_DELIVERY_ENTERED'),

        # Obstetric history
        'gravidity': _safe_float(fields.get('GRAVIDITY')),
        'parity': _safe_float(fields.get('PARITY')),

        # Clinical events
        'seizure_documented': fields.get('SEIZURE'),
        'mgso4_exposure': fields.get('MGSO4'),
        'pulm_oedema_documented': _flag(fields.get('PULM_OEDEMA')),
        'icu_admission': _flag(fields.get('ICU_ADMISSION')),
        'maternal_death': _flag(fields.get('MATERNAL_DEATH')),
        'dic_documented': _flag(fields.get('DIC')),
        'blood_transfusion': _flag(fields.get('BLOOD_TRANSFUSION')),
        'hepatic_failure': _flag(fields.get('HEPATIC_FAILURE')),
        'neonatal_death': _flag(fields.get('NEONATAL_DEATH')),
        'rds': _flag(fields.get('RDS')),
        'nec': _flag(fields.get('NEC')),
        'ivh': _flag(fields.get('IVH')),

        # Dating
        'firstUssDate': fields.get('USS_DATE'),
        'firstUssGa': fields.get('USS_GA'),
        'edd': fields.get('EDD'),

        # Source docs
        'sourceDocs': {'ultrasound': fields.get('USS_DATE') is not None},
    }

    # --- Run original ISSHP-2021 engine ---
    orig_results = run_full_derivation(case_data)

    # --- Run DV-01 through DV-30 engine ---
    dv_bundle = None
    if DV_ENGINE_AVAILABLE:
        try:
            dv_bundle = run_dv_engine(case_data)
        except Exception as e:
            dv_bundle = {'error': str(e), 'engine': 'PROTECT-DV-2026.08'}

    # --- Persist derivation results ---
    db.query(DerivationResult).filter_by(participant_id=participant.id).delete()
    for criterion_id, result in orig_results.items():
        if isinstance(result, CriterionResult):
            dr = DerivationResult(
                participant_id=participant.id,
                criterion_id=result.criterion_id,
                criterion_name=result.criterion_name,
                met=result.met,
                formula=result.formula,
                inputs=result.inputs,
                source_fields=result.source_fields,
                first_date_met=result.first_date_met,
                gestational_age_at_event=result.gestational_age_at_event,
                rule_version=result.rule_version,
            )
            db.add(dr)
    db.commit()

    # Build response
    criteria_list = []
    for k, r in orig_results.items():
        if isinstance(r, CriterionResult):
            criteria_list.append({
                'criterion_id': r.criterion_id,
                'criterion_name': r.criterion_name,
                'met': r.met,
                'formula': r.formula,
                'inputs': r.inputs,
                'source_fields': r.source_fields,
                'first_date_met': r.first_date_met.isoformat() if r.first_date_met else None,
                'rule_version': r.rule_version,
            })

    return {
        'subject_id': subject_id,
        'criteria': criteria_list,
        'dv_bundle': dv_bundle,
        'evidence_completeness_score': orig_results.get('evidence_completeness_score', 0),
        'missing_anchors': orig_results.get('missing_anchors', []),
        'certainty_gate_passed': orig_results.get('certainty_gate_passed', False),
        'derived_at': datetime.utcnow().isoformat(),
        'rule_version': 'PROTECT-DV-2026.08',
    }
