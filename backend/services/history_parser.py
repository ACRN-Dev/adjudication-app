import re
import hashlib
from datetime import datetime
from models.history import PatientHistory, PatientHistoryField, PatientRiskSummary

HISTORY_FORMS = {"Screening |V01", "Medical History / Prior & Concomitant Medications + Sync"}
HISTORY_DOMAINS = {
    "Obstetric history": "obstetric",
    "Medical Conditions": "medical",
    "Family history": "family",
    "Allergies": "allergy_surgery",
    "Social History": "social",
    "Demographics": "baseline",
    "Concomitant Medications": "medications",
    "Prior Medications": "medications",
    "Medications": "medications",
}

def is_history_form(form_title):
    return form_title in HISTORY_FORMS

def normalize_field_label(label):
    if not label:
        return ""
    # Collapse multiple spaces and trim
    norm = re.sub(r'\s+', ' ', label).strip()
    return norm

def make_field_key(label):
    norm = normalize_field_label(label).lower()
    return re.sub(r'[^a-z0-9]+', '_', norm).strip('_')

def parse_partial_date(value_str):
    if not value_str or str(value_str).strip() in {"0", ""}:
        return None, None
    v = str(value_str).strip().split()[0]
    parts = v.split('/')
    if len(parts) == 3:
        m, d, y = parts
        if m == '0' and d == '0':
            return y, "year-only"
        if d == '0':
            return f"{m.zfill(2)}/{y}", "month-year"
    return v, "full"

def parse_php_serialized_instances(text):
    """
    Parses strings like:
    #1 - s:12:"Hypertension";
    #2 - s:7:"ongoing";
    #1 - N;
    #1 - s:19:"6/16/2026 00:00:00 ";
    Returns a dict mapping instance index (int) -> string value.
    If there are no instance prefixes, returns {None: text}.
    """
    if not text or str(text).strip() in {"0", ""}:
        return {None: None}
    
    text = str(text).strip()
    
    # Check if it has instance prefixes
    if not re.search(r'#\d+\s*-', text):
        return {None: text}
        
    results = {}
    
    # Split by instance prefixes
    parts = re.split(r'(#\d+\s*-)', text)
    
    current_idx = None
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r'#(\d+)\s*-', p)
        if m:
            current_idx = int(m.group(1))
        else:
            if current_idx is not None:
                val = p
                # Check for N; or N
                if val == 'N;' or val == 'N':
                    results[current_idx] = None
                else:
                    # Extract string from s:<len>:"<val>";
                    sm = re.search(r's:\d+:"(.*?)";?', val, re.DOTALL)
                    if sm:
                        results[current_idx] = sm.group(1)
                    else:
                        # Fallback for plain text or missing quotes
                        val = re.sub(r';$', '', val)
                        results[current_idx] = val
                current_idx = None
                
    return results

def sanitize_audit_trail(audit_str):
    if not audit_str or audit_str == "0":
        return None, None
    # Usually: "Surname, Firstname - 04/Mar/2026 01:20:21 PM CAT"
    parts = audit_str.split(' - ')
    if len(parts) == 2:
        actor, dt_str = parts
        actor_hash = hashlib.sha256(actor.strip().encode()).hexdigest()
        try:
            dt = datetime.strptime(dt_str.strip(), "%d/%b/%Y %I:%M:%S %p %Z")
            return dt, actor_hash
        except ValueError:
            # Fallback format or timezone issues
            return None, actor_hash
    return None, None

def process_history_row(db, batch, participant, row, row_no):
    page_title = (row.get("Page Title") or "").strip()
    domain = HISTORY_DOMAINS.get(page_title)
    if not domain:
        return
        
    field_label_raw = (row.get("Field Label") or "").strip()
    if not field_label_raw:
        return
        
    field_type = (row.get("Field type") or "").strip()
    data_value = row.get("Data Value")
    if data_value is None or str(data_value).strip() == "":
        data_value = row.get("Data Input")
        
    audit_trail = row.get("Audit Trails")
    
    field_key = make_field_key(field_label_raw)
    instances = parse_php_serialized_instances(data_value)
    
    signed_at, actor_hash = sanitize_audit_trail(audit_trail)
    
    for idx, val in instances.items():
        if val == "0" and field_type != "numeric":
            val = None # 0 is typically empty in Realtime exports unless numeric
            
        precision = None
        if field_type == "date_time" and val:
            val, precision = parse_partial_date(val)
            
        if val is not None:
            val = str(val).strip()
            
        # Tri-state handling: keep Yes / No / Not known verbatim
        # (Already handled since we store it as text)

        # Idempotency check:
        existing = db.query(PatientHistoryField).filter_by(
            participant_id=participant.id,
            domain=domain,
            field_key=field_key,
            instance_index=idx,
            source_batch_id=batch.id
        ).first()
        
        if existing:
            # Update if changed
            existing.value = val
            existing.value_precision = precision
            existing.signed_at = signed_at
            existing.audit_actor_hash = actor_hash
        else:
            pf = PatientHistoryField(
                participant_id=participant.id,
                subject_id=participant.blinded_subject_id,
                domain=domain,
                field_key=field_key,
                field_label_raw=normalize_field_label(field_label_raw),
                field_type=field_type,
                value=val,
                value_precision=precision,
                instance_index=idx,
                signed_at=signed_at,
                audit_actor_hash=actor_hash,
                source_batch_id=batch.id
            )
            db.add(pf)
            
    # Record the patient history container if not present
    ph = db.query(PatientHistory).filter_by(
        participant_id=participant.id, 
        source_form=row.get("Form Title")
    ).first()
    if not ph:
        ph = PatientHistory(
            participant_id=participant.id,
            subject_id=participant.blinded_subject_id,
            source_form=row.get("Form Title"),
            form_version=row.get("Form Version"),
            source_file=batch.filename
        )
        db.add(ph)

def get_field_val(fields, key, idx=None):
    for f in fields:
        if f.field_key == key:
            if idx is None or f.instance_index == idx:
                return f.value
    return None

def compute_risk_summary(fields):
    chips = set()
    
    # 1. Prior PE
    if get_field_val(fields, "does_the_participant_have_any_history_of_preeclampsia_in_previous_pregnancies") == "Yes":
        chips.add("Prior PE")
        
    # 2. Prior Severe PE
    if get_field_val(fields, "does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies") == "Yes":
        chips.add("Prior Severe PE")
        
    # 3. Prior Eclampsia
    if get_field_val(fields, "does_the_participant_have_any_history_of_eclampsia_in_previous_pregnancies") == "Yes":
        chips.add("Prior Eclampsia")
        
    # 4. Prior HELLP
    if get_field_val(fields, "does_the_participant_have_any_history_of_hellp_in_previous_pregnancies") == "Yes":
        chips.add("Prior HELLP")
        
    # 5. Prior IUGR
    if get_field_val(fields, "does_the_participant_have_any_history_of_iugr_in_previous_pregnancies") == "Yes":
        chips.add("Prior IUGR")
        
    # 6. Prior gestational HTN
    if get_field_val(fields, "does_participant_have_any_history_of_raised_blood_pressure_during_pregnancy") == "Yes":
        chips.add("Prior gestational HTN")
        
    # 7. Prior stillbirth
    sb = get_field_val(fields, "number_of_still_births")
    try:
        sb_int = int(sb)
        if sb_int > 0:
            chips.add(f"Prior stillbirth ({sb_int})")
    except (ValueError, TypeError):
        sb_int = 0
        
    # 8. Pre-existing chronic HTN
    # Check medical conditions for Hypertension
    chronic_htn = False
    for f in fields:
        if f.field_key == "medical_condition" and f.value and "Hypertension" in f.value:
            chronic_htn = True
            break
    if chronic_htn:
        chips.add("Pre-existing chronic HTN")
        
    # 9. Pre-gestational diabetes
    pregestational_diabetes = False
    for f in fields:
        if f.field_key == "medical_condition" and f.value and "Diabetes" in f.value:
            pregestational_diabetes = True
            break
    if pregestational_diabetes:
        chips.add("Pre-gestational diabetes")
        
    # 10. Family history PE
    # (Assuming a key exists for this, e.g., family_history_of_preeclampsia)
    # Check all fields in family domain
    for f in fields:
        if f.domain == "family" and "preeclampsia" in str(f.value).lower():
            chips.add("Family history PE")
            break
            
    # 11. Prior PE-indicated C-section
    for f in fields:
        if f.field_key == "reason_for_cesarean_section" and f.value:
            if "Preeclampsia" in f.value or "Eclampsia" in f.value:
                chips.add("Prior PE-indicated C-section")
                
    # 12. Nulliparous
    prev_preg = get_field_val(fields, "has_participant_had_any_previous_pregnancies")
    if prev_preg == "No":
        chips.add("Nulliparous")
        
    # Parity calculations
    try: gravidity = int(get_field_val(fields, "if_yes_how_many_previous_pregnancies") or 0)
    except: gravidity = 0
    if prev_preg == "Yes" and gravidity == 0:
        gravidity = 1
        
    try: parity = int(get_field_val(fields, "number_of_live_births") or 0)
    except: parity = 0
    
    try: miscarriages = int(get_field_val(fields, "number_of_miscarriages") or 0)
    except: miscarriages = 0
    
    try: vag = int(get_field_val(fields, "number_of_vaginal_deliveries") or 0)
    except: vag = 0
    
    try: cs = int(get_field_val(fields, "number_of_cesarean_sections") or 0)
    except: cs = 0
    
    parity_summary = f"G{gravidity} P{parity} +{miscarriages}M +{sb_int}SB · {vag} SVD / {cs} CS"
    
    return {
        "chips": sorted(list(chips)),
        "parity_summary": parity_summary,
        "gravidity": gravidity,
        "parity": parity,
        "miscarriages": miscarriages,
        "stillbirths": sb_int,
        "vaginal_deliveries": vag,
        "c_sections": cs,
        "chronic_htn": chronic_htn,
        "pregestational_diabetes": pregestational_diabetes
    }

def calculate_history_completeness(fields):
    # Determine if obstetric and medical domains are populated
    domains = {f.domain for f in fields}
    if "obstetric" in domains and "medical" in domains:
        return 1.0
    elif "obstetric" in domains or "medical" in domains:
        return 0.5
    return 0.0

def finalize_history(db, participant):
    # Run amber flag evaluation and risk summary
    fields = db.query(PatientHistoryField).filter_by(participant_id=participant.id).all()
    if not fields:
        return
        
    # Evaluate Amber flags:
    # Example: If "Did the participant have any Cesarean sections?" == "Yes", but "Number of Cesarean sections" == 0 or empty.
    # Group fields by instance or globally.
    for f in fields:
        f.amber_flag = False
        f.flag_reason = None
        
        # Example condition logic:
        if f.field_key == "did_the_participant_have_any_cesarean_sections" and f.value == "Yes":
            cs = get_field_val(fields, "number_of_cesarean_sections", f.instance_index)
            if not cs or cs == "0":
                f.amber_flag = True
                f.flag_reason = "Gate is Yes but detail is empty"
                
    db.commit()

    risk_data = compute_risk_summary(fields)
    
    summary = db.query(PatientRiskSummary).filter_by(participant_id=participant.id).first()
    if not summary:
        summary = PatientRiskSummary(
            participant_id=participant.id,
            subject_id=participant.blinded_subject_id
        )
        db.add(summary)
        
    for k, v in risk_data.items():
        setattr(summary, k, v)
        
    completeness = calculate_history_completeness(fields)
    summary.completeness_score = completeness
    participant.history_completeness = completeness
    summary.updated_at = datetime.utcnow()
    
    db.commit()
