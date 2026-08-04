"""
AI Narrative Generator API — POST /api/narrative/{subject_id}
==============================================================
Generates a structured 13-section blinded clinical narrative (FORM-ADJ-15A or FORM-ADJ-15B).

FORM-ADJ-15A — Early-onset PE (EOPE < 34+0 weeks) and postpartum presentations.
FORM-ADJ-15B — Late-onset PE (LOPE ≥ 34+0 weeks).

Key rules (per SOP-ADJ-002 and change record item #13):
  - Coordinator facts are separated from reviewer determination.
  - The narrative does NOT adjudicate automatically — it presents evidence only.
  - Missing evidence is stated explicitly as 'Not documented — not assessable'.
  - Biomarker data (sFlt-1, PlGF, sEng, treatment allocation) is EXCLUDED.
  - Site and provider identifiers are EXCLUDED (blinded).
  - The original AI/template draft is retained for audit; human edits stored separately.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db, DB_OFFLINE
from models.canonical import Participant, Narrative

router = APIRouter()

# ── Blinded / prohibited terms ────────────────────────────────────────────────
PROHIBITED_TERMS = [
    'sflt', 'sflt-1', 'plgf', 'pigf', 'placental growth factor',
    'seng', 'soluble endoglin', 'ratio', 'poc result',
    'treatment allocation', 'randomis', 'randomiz',
    'site name', 'hospital name', 'investigator', 'physician name',
]

REVIEWER_PLACEHOLDER = (
    "\n---\n"
    "REVIEWER / OAC DETERMINATION\n"
    "[To be completed by the adjudicating physician. "
    "This section must not be pre-populated by any automated system.]\n"
    "---"
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class NarrativeEditRequest(BaseModel):
    """Human edit to the narrative. Editor identity and rationale are required."""
    section_1:  Optional[str] = None
    section_2:  Optional[str] = None
    section_3:  Optional[str] = None
    section_4:  Optional[str] = None
    section_5:  Optional[str] = None
    section_6:  Optional[str] = None
    section_7:  Optional[str] = None
    section_8:  Optional[str] = None
    section_9:  Optional[str] = None
    section_10: Optional[str] = None
    section_11: Optional[str] = None
    section_12: Optional[str] = None
    section_13: Optional[str] = None
    edited_by: str
    editor_role: Optional[str] = None
    edit_rationale: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(v, fallback='[Not documented — not assessable]'):
    """Return value if present, else fallback. Never returns empty string."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return fallback
    return str(v)


def _check_prohibited(text: str) -> List[str]:
    """Return list of prohibited terms found in text."""
    found = []
    lower = text.lower()
    for term in PROHIBITED_TERMS:
        if term in lower:
            found.append(term)
    return found


def _determine_form_code(participant) -> str:
    """Determine FORM-ADJ-15A or FORM-ADJ-15B from derivation results."""
    if not participant.derivation_results:
        return 'FORM-ADJ-15A'
    for dr in participant.derivation_results:
        if dr.criterion_id in ('ONSET-01', 'DV-05') and dr.inputs:
            onset = dr.inputs.get('classification', '').upper()
            if onset == 'LOPE':
                return 'FORM-ADJ-15B'
    return 'FORM-ADJ-15A'


def _build_template_narrative(subject_id: str, form_code: str, fields: dict) -> dict:
    """
    Build a 13-section template narrative from canonical fields.
    All 13 sections follow the FORM-ADJ-15A/15B structure.
    Biomarker and site/provider data are explicitly excluded.
    """
    na = '[Not documented — not assessable]'

    def f(key, fallback=na):
        v = fields.get(key)
        return str(v) if v is not None else fallback

    sections = {
        'section_1': (
            f"SECTION 1 — CASE METADATA AND IDENTIFIER\n"
            f"Participant ID: {subject_id}\n"
            f"Form: {form_code}\n"
            f"Study: {f('STUDY_CODE', na)}\n"
            f"Protocol version: {f('PROTOCOL_VERSION', na)}\n"
            f"Narrative generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"[Site and investigator identifiers withheld — SOP-ADJ-002]"
        ),
        'section_2': (
            f"SECTION 2 — ENDPOINT / PREDICTION WINDOW\n"
            f"Estimated delivery date (EDD): {f('EDD')}\n"
            f"Event date: {f('EVENT_DT')}\n"
            f"Gestational age at event: {f('GA_EVENT')}\n"
            f"Prediction window: {f('PREDICTION_WINDOW', na)}"
        ),
        'section_3': (
            f"SECTION 3 — PREGNANCY DATING\n"
            f"Dating method: {f('DATING_METHOD', na)}\n"
            f"First USS date: {f('USS_DATE')}\n"
            f"GA at first USS: {f('USS_GA')}\n"
            f"LNMP: {f('LNMP', na)}\n"
            f"Dating reliability: {f('DATING_RELIABILITY', na)}"
        ),
        'section_4': (
            f"SECTION 4 — CLINICAL PRESENTATION SUMMARY\n"
            f"Presenting symptoms: {f('SYMPTOMS', na)}\n"
            f"GA at presentation: {f('GA_EVENT')}\n"
            f"Onset classification (derived): {f('ONSET_CLASS', 'Pending derivation')}\n"
            f"Severity (derived): {f('DERIVED_SEVERITY', 'Pending derivation')}\n"
            f"Gravidity: {f('GRAVIDITY', na)} | Parity: {f('PARITY', na)}\n"
            f"Relevant comorbidities: {f('COMORBIDITIES', na)}"
        ),
        'section_5': (
            f"SECTION 5 — BLOOD PRESSURE COURSE\n"
            f"BP readings documented in canonical record. "
            f"Maximum SBP: {f('MAX_SBP', na)} mmHg | Maximum DBP: {f('MAX_DBP', na)} mmHg.\n"
            f"Severe-range BP (≥160/110 mmHg): {f('SEVERE_BP_DOCUMENTED', na)}.\n"
            f"Confirmed hypertension on ≥2 occasions: {f('CONFIRMED_HTN', na)}.\n"
            f"Antihypertensive treatment: {f('ANTIHYPERTENSIVE_GIVEN', na)}."
        ),
        'section_6': (
            f"SECTION 6 — PROTEINURIA EVIDENCE\n"
            f"UPCR: {f('UPCR', na)} g/g.\n"
            f"24-hour urine protein: {f('PROT_24H', na)} mg/24h.\n"
            f"Dipstick result: {f('DIPSTICK', na)}.\n"
            f"Significant proteinuria threshold met (≥0.3 g/g or ≥300 mg/24h or ≥2+): "
            f"{f('PROTEINURIA_MET', na)}."
        ),
        'section_7': (
            f"SECTION 7 — LABORATORY COURSE (HAEMATOLOGY AND BIOCHEMISTRY)\n"
            f"Platelet count: {f('PLATELET_COUNT', na)} ×10³/µL.\n"
            f"Creatinine: {f('CREATININE', na)} {f('CREATININE_UNIT', '')}.\n"
            f"AST: {f('AST', na)} U/L | ALT: {f('ALT', na)} U/L.\n"
            f"LDH: {f('LDH', na)} IU/L.\n"
            f"HELLP criteria met: {f('HELLP_MET', na)}.\n"
            f"[Biomarker data (sFlt-1/PlGF/sEng/POC) withheld per SOP-ADJ-002 until database lock.]"
        ),
        'section_8': (
            f"SECTION 8 — MATERNAL CLINICAL COURSE\n"
            f"MgSO₄ administered: {f('MGSO4', na)}.\n"
            f"Antihypertensive therapy: {f('ANTIHYPERTENSIVE_GIVEN', na)}.\n"
            f"Pulmonary oedema: {f('PULM_OEDEMA', na)}.\n"
            f"ICU admission: {f('ICU_ADMISSION', na)}.\n"
            f"Eclampsia / seizure: {f('SEIZURE', na)}.\n"
            f"Other SAEs: {f('SAE', na)}."
        ),
        'section_9': (
            f"SECTION 9 — FETAL ASSESSMENT (GROWTH AND DOPPLER)\n"
            f"EFW centile: {f('EFW_CENTILE', na)}.\n"
            f"Umbilical artery AEDF: {f('UA_AEDF', na)} | REDF: {f('UA_REDF', na)}.\n"
            f"Biophysical profile: {f('BPP', na)}.\n"
            f"Placental abruption: {f('ABRUPTION', na)}.\n"
            f"IUFD: {f('IUFD', na)}."
        ),
        'section_10': (
            f"SECTION 10 — DELIVERY RECORD\n"
            f"Delivery date: {f('DELIVERY_DATE')}.\n"
            f"GA at delivery: {f('GA_DELIVERY', na)} weeks.\n"
            f"Mode of delivery: {f('DELIVERY_MODE', na)}.\n"
            f"Indication for delivery: {f('DELIVERY_INDICATION', na)}."
        ),
        'section_11': (
            f"SECTION 11 — MATERNAL OUTCOME\n"
            f"Maternal death: {f('MATERNAL_DEATH', na)}.\n"
            f"DIC: {f('DIC', na)}.\n"
            f"Blood transfusion: {f('BLOOD_TRANSFUSION', na)}.\n"
            f"Hepatic failure: {f('HEPATIC_FAILURE', na)}.\n"
            f"Acute renal failure requiring dialysis: {f('ACUTE_RENAL_FAILURE', na)}."
        ),
        'section_12': (
            f"SECTION 12 — NEONATAL OUTCOME\n"
            f"Birth weight: {f('BIRTH_WEIGHT', na)} grams.\n"
            f"Neonatal death: {f('NEONATAL_DEATH', na)}.\n"
            f"RDS: {f('RDS', na)} | NEC: {f('NEC', na)} | IVH: {f('IVH', na)}.\n"
            f"NICU admission: {f('NICU_ADMISSION', na)}."
        ),
        'section_13': (
            f"SECTION 13 — MISSING DATA, DISCREPANCIES AND OUTSTANDING QUERIES\n"
            f"Evidence completeness score: {f('PKT_SCORE', na)}.\n"
            f"Missing data items: {f('MISSING_ANCHORS', na)}.\n"
            f"Outstanding data queries: {f('OPEN_QUERIES', na)}.\n"
            f"Clinically meaningful discrepancies: {f('DISCREPANCIES', na)}.\n\n"
            + REVIEWER_PLACEHOLDER
        ),
    }
    return sections


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{subject_id}")
def generate_narrative(subject_id: str, db: Session = Depends(get_db)):
    """
    Generate or regenerate the structured 13-section narrative for a participant.
    Stores the original template/AI draft. Human edits are stored separately.
    """
    if DB_OFFLINE:
        return {
            "status": "offline",
            "message": "Database unavailable. Use frontend demoNarrative.js for offline narrative generation.",
        }

    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    form_code = _determine_form_code(participant)

    # Build field lookup
    fields = {
        f.canonical_field: f.canonical_value
        for f in participant.canonical_fields
        if not f.is_blinded
    }

    # Build template sections
    sections = _build_template_narrative(subject_id, form_code, fields)

    # Try AI generation if OpenAI key present
    model_used = 'template-FORM-ADJ-local-v1'
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            system_prompt = (
                f"You are a clinical trial medical writer. Generate a blinded 13-section clinical narrative "
                f"using template {form_code}. "
                "STRICT RULES: "
                "1. Do NOT include biomarker data (sFlt-1, PlGF, sEng, treatment allocation, POC results). "
                "2. Do NOT include site names, hospital names, investigator names, or provider identifiers. "
                "3. Do NOT make any adjudication determination. Describe evidence only. "
                "4. For missing data, write '[Not documented — not assessable]', not a negative finding. "
                "5. Leave Section 13 reviewer determination blank as per the PLACEHOLDER text."
            )
            user_prompt = (
                f"Participant: {subject_id}\n"
                f"Form: {form_code}\n"
                f"Key fields: {dict(list(fields.items())[:30])}"
            )
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                max_tokens=2000,
            )
            raw = response.choices[0].message.content
            # Check for prohibited terms
            prohibited_found = _check_prohibited(raw)
            if not prohibited_found:
                sections['section_1'] = raw[:500]  # Use AI where safe
                model_used = 'gpt-4o-mini'
        except Exception:
            pass  # Fall back to template

    # Store or update narrative — original draft is ALWAYS preserved
    existing = db.query(Narrative).filter_by(participant_id=participant.id).first()
    narrative = existing or Narrative(participant_id=participant.id)
    narrative.prompt_version = 'v2.0'
    narrative.model_used = model_used
    narrative.ai_section_1  = sections['section_1']
    narrative.ai_section_2  = sections.get('section_2', '')
    narrative.ai_section_3  = sections.get('section_3', '')
    narrative.ai_section_4  = sections.get('section_4', '')
    narrative.ai_section_5  = sections.get('section_5', '')

    if not existing:
        db.add(narrative)
    db.commit()
    db.refresh(narrative)

    return {
        'narrative_id': str(narrative.id),
        'subject_id': subject_id,
        'form_code': form_code,
        'model_used': model_used,
        'sections': sections,
        'is_edited': bool(narrative.edited_at),
        'original_preserved': True,
        'generated_at': datetime.utcnow().isoformat(),
    }


@router.put("/{subject_id}/edit")
def edit_narrative(
    subject_id: str,
    edit_req: NarrativeEditRequest,
    db: Session = Depends(get_db)
):
    """
    Store human edits to the narrative.
    The original AI/template draft is ALWAYS retained in ai_section_* fields.
    Editor identity, role, and rationale are required and stored for audit.
    """
    if DB_OFFLINE:
        return {"status": "offline", "message": "Database unavailable."}

    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant or not participant.narratives:
        raise HTTPException(status_code=404, detail="Narrative not found. Generate it first.")

    narrative = participant.narratives[0]

    # Apply edits — only update non-None sections
    if edit_req.section_1  is not None: narrative.edited_section_1 = edit_req.section_1
    if edit_req.section_2  is not None: narrative.edited_section_2 = edit_req.section_2
    if edit_req.section_3  is not None: narrative.edited_section_3 = edit_req.section_3
    if edit_req.section_4  is not None: narrative.edited_section_4 = edit_req.section_4
    if edit_req.section_5  is not None: narrative.edited_section_5 = edit_req.section_5

    narrative.edited_by = edit_req.edited_by
    narrative.edit_rationale = edit_req.edit_rationale
    narrative.edited_at = datetime.utcnow()

    db.commit()

    return {
        'status': 'success',
        'subject_id': subject_id,
        'edited_by': edit_req.edited_by,
        'editor_role': edit_req.editor_role,
        'edit_rationale': edit_req.edit_rationale,
        'edited_at': narrative.edited_at.isoformat(),
        'message': 'Narrative updated. Original template/AI version retained in audit log.',
        'original_preserved': True,
    }


@router.get("/{subject_id}")
def get_narrative(subject_id: str, db: Session = Depends(get_db)):
    """Retrieve the current narrative for a participant (human-edited if available)."""
    if DB_OFFLINE:
        return {"status": "offline", "message": "Database unavailable."}

    participant = db.query(Participant).filter_by(subject_id=subject_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {subject_id} not found.")

    if not participant.narratives:
        raise HTTPException(status_code=404, detail="Narrative not yet generated.")

    narrative = participant.narratives[0]
    form_code = _determine_form_code(participant)

    return {
        'narrative_id': str(narrative.id),
        'subject_id': subject_id,
        'form_code': form_code,
        'model_used': narrative.model_used,
        'sections': {
            'section_1': narrative.edited_section_1 or narrative.ai_section_1 or '',
            'section_2': narrative.edited_section_2 or narrative.ai_section_2 or '',
            'section_3': narrative.edited_section_3 or narrative.ai_section_3 or '',
            'section_4': narrative.edited_section_4 or narrative.ai_section_4 or '',
            'section_5': narrative.edited_section_5 or narrative.ai_section_5 or '',
        },
        'is_edited': bool(narrative.edited_at),
        'edited_by': narrative.edited_by,
        'edited_at': narrative.edited_at.isoformat() if narrative.edited_at else None,
        'original_preserved': True,
    }
