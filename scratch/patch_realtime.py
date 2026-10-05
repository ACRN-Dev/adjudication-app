with open('backend/api/realtime.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        canonical_visit = canonical_visits.get(visit_number)
        reviewer_record = reviewer_records.get(visit_number)
        ga_label = f"{v.gestational_age_days // 7} weeks, {v.gestational_age_days % 7} days" if (v.gestational_age_days and v.gestational_age_days >= 45) else None
        visits.append({
            "id":str(v.id),"name":v.scheduled_visit_code,"visit_number":visit_number,"occurrence":v.visit_occurrence,
            "date":v.visit_datetime,"ga_days":v.gestational_age_days,"ga":ga_label,"gestationalLabel":ga_label,"form":v.form_title,
            "form_version":v.form_version,"""

replacement = """        canonical_visit = canonical_visits.get(visit_number)
        reviewer_record = reviewer_records.get(visit_number)
        ga_label = f"{v.gestational_age_days // 7} weeks, {v.gestational_age_days % 7} days" if (v.gestational_age_days and v.gestational_age_days >= 45) else None

        obs_dts = [o.observation_datetime for o in v.observations if o.observation_datetime]
        resolved_date = v.visit_datetime or (min(obs_dts) if obs_dts else None)

        not_performed_reason = None
        for o in v.observations:
            fld = (o.source_field_label or "").lower()
            val = str(o.raw_source_value or o.parsed_text_value or "").strip()
            if "not performing" in fld or "not performed" in fld or "missed" in fld or val.lower() in {"delivered", "missed visit", "withdrew", "lost to follow-up"}:
                not_performed_reason = val
                break

        visits.append({
            "id":str(v.id),"name":v.scheduled_visit_code,"visit_number":visit_number,"occurrence":v.visit_occurrence,
            "date":resolved_date,"ga_days":v.gestational_age_days,"ga":ga_label,"gestationalLabel":ga_label,"form":v.form_title,
            "form_version":v.form_version,
            "not_performed_reason": not_performed_reason,"""

# Normalize newlines for matching
content_nl = content.replace('\r\n', '\n')
target_nl = target.replace('\r\n', '\n')
replacement_nl = replacement.replace('\r\n', '\n')

if target_nl in content_nl:
    updated = content_nl.replace(target_nl, replacement_nl, 1)
    with open('backend/api/realtime.py', 'w', encoding='utf-8') as f:
        f.write(updated)
    print('SUCCESSFULLY UPDATED realtime.py')
else:
    print('TARGET NOT FOUND')
