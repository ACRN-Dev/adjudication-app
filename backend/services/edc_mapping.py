"""Adapter from common wide EDC and Oracle Clinical One exports into the canonical long-form import contract."""
from collections import defaultdict
from services.realtime_mapping import DIRECT_ALIASES

EDC_ID_COLUMNS = ("SUBJID", "SubjectID", "USUBJID", "ParticipantID", "Subject ID", "Screening Number", "Subject Number")
EDC_VISIT_COLUMNS = ("EVENT", "VISIT", "VISIT_NAME", "EventName", "Visit/Event Title")
EDC_DATE_COLUMNS = ("EVENT_DT", "VISIT_DATE", "VisitDate", "Date & Time")
REALTIME_SIGNATURE_COLUMNS = {"Field Label", "Data Value", "Data Input", "Field type", "Export Variable Name"}

CLINICAL_ONE_SIGNATURE = {
    "Subject ID", "Screening Number", "Visit/Event Title", "Form Title", "Question Label", "Value"
}

LAB_FORMS = {"CLINICAL CHEMISTRY", "HEMATOLOGY", "BIOMARKER ANALYSIS", "URINALYSIS"}


def is_clinical_one_schema(fieldnames):
    names = {str(x or "").strip() for x in fieldnames or []}
    return CLINICAL_ONE_SIGNATURE.issubset(names)


def is_edc_schema(fieldnames):
    names = {str(x or "").strip() for x in fieldnames or []}
    if is_clinical_one_schema(names):
        return True
    if bool(names.intersection(REALTIME_SIGNATURE_COLUMNS)):
        return False
    return bool(names.intersection(EDC_ID_COLUMNS)) and bool(names.intersection(EDC_VISIT_COLUMNS + EDC_DATE_COLUMNS))


def _first(row, columns):
    return next((str(row.get(c) or "").strip() for c in columns if str(row.get(c) or "").strip()), "")


def normalize_edc_rows(rows):
    """Yield RealTime-shaped rows from wide EDC exports."""
    excluded = 0
    for source_row, row in enumerate(rows, 2):
        subject = _first(row, EDC_ID_COLUMNS)
        if not subject:
            excluded += 1
            continue
        visit = _first(row, EDC_VISIT_COLUMNS)
        visit_date = _first(row, EDC_DATE_COLUMNS)
        form = visit or ("EXCLUDED VISIT - MISSING KEY FIELDS" if not visit_date else "UNSCHEDULED EDC VISIT")
        base = {
            "MRN": subject, "Screening #": subject, "Randomization #": "",
            "Form Title": form, "Form Version": str(row.get("FORM_VERSION") or "EDC"),
            "Page Title": "EDC Wide Export", "Field type": "EDC",
            "Audit Trails": "", "_EDC_SOURCE_ROW": source_row,
            "_EDC_MISSING_VISIT_KEY": not bool(visit or visit_date),
        }
        for column, value in row.items():
            alias = str(column or "").strip().lower().replace(" ", "_")
            if alias not in DIRECT_ALIASES:
                continue
            yield {**base, "Field Label": column, "Export Variable Name": alias,
                   "Data Input": str(value or ""), "Data Value": str(value or "")}


def normalize_clinical_one_rows(rows):
    """
    Normalizes item-level Oracle Clinical One Subject Data Report rows into canonical long-form rows.
    Collates repeating lab test tables (CLINICAL CHEMISTRY, HEMATOLOGY) into discrete observation records
    and properly extracts vital signs, delivery outcomes, and newborn assessments.
    """
    current_key = None
    block = []

    def flush_block(block_rows):
        if not block_rows:
            return

        first = block_rows[0]
        subj = (first.get("Screening Number") or first.get("Subject Number") or first.get("Subject ID") or "").strip()
        if not subj:
            return

        visit = (first.get("Visit/Event Title") or "UNSCHEDULED").strip()
        form = (first.get("Form Title") or "CLINICAL").strip()
        form_title = f"{visit} - {form}" if visit else form
        version = (first.get("Study Version") or "1.0").strip()

        base = {
            "MRN": subj,
            "Screening #": subj,
            "Randomization #": "",
            "Form Title": form_title,
            "Form Version": version,
            "Page Title": visit,
            "Field type": "EDC_CLINICAL_ONE",
            "_EDC_MISSING_VISIT_KEY": False,
        }

        # Check if this form contains repeating lab sections
        is_lab = any(lab in form.upper() for lab in LAB_FORMS)
        if is_lab:
            repeating = defaultdict(dict)
            non_repeating = []
            for r in block_rows:
                sec = (r.get("Repeating Section Number") or "").strip()
                q = (r.get("Question Label") or "").strip()
                val = (r.get("Value") or "").strip()
                if sec and sec != "N/A":
                    repeating[sec][q] = val
                    if r.get("Unit of Measure") and r.get("Unit of Measure") != "N/A":
                        repeating[sec]["_unit"] = r.get("Unit of Measure")
                    if r.get("Type of Change"):
                        repeating[sec]["_change"] = r.get("Type of Change")
                    if r.get("Date & Time"):
                        repeating[sec]["_date"] = r.get("Date & Time")
                    if r.get("User Name"):
                        repeating[sec]["_user"] = r.get("User Name")
                    repeating[sec]["_source_row"] = r.get("_EDC_SOURCE_ROW", 0)
                else:
                    non_repeating.append(r)

            for sec, data in repeating.items():
                test_name = data.get("Lab Test") or data.get("Test Name")
                result = data.get("Lab Result") or data.get("Result")
                unit = data.get("Lab Unit") or data.get("_unit") or ""
                if test_name and result and result not in ("N/A", "Flag: Unknown", ""):
                    audit_str = f"User: {data.get('_user', '')} | Change: {data.get('_change', '')} | Date: {data.get('_date', '')}"
                    alias = test_name.strip().lower().replace(" ", "_")
                    yield {
                        **base,
                        "Field Label": test_name,
                        "Export Variable Name": alias,
                        "Data Input": f"{result} {unit}".strip(),
                        "Data Value": str(result).strip(),
                        "Audit Trails": audit_str,
                        "_EDC_SOURCE_ROW": data.get("_source_row", 0),
                    }

            block_rows = non_repeating

        # Collate repeating PHYSICAL EXAMINATION sections
        if "PHYSICAL EXAMINATION" in form.upper():
            pe_repeating = defaultdict(dict)
            pe_non_repeating = []
            for r in block_rows:
                sec = (r.get("Repeating Section Number") or "").strip()
                q = (r.get("Question Label") or "").strip()
                val = (r.get("Value") or "").strip()
                if sec and sec != "N/A":
                    pe_repeating[sec][q] = val
                    if r.get("Type of Change"):
                        pe_repeating[sec]["_change"] = r.get("Type of Change")
                    if r.get("Date & Time"):
                        pe_repeating[sec]["_date"] = r.get("Date & Time")
                    if r.get("User Name"):
                        pe_repeating[sec]["_user"] = r.get("User Name")
                    pe_repeating[sec]["_source_row"] = r.get("_EDC_SOURCE_ROW", 0)
                else:
                    pe_non_repeating.append(r)

            for sec, data in pe_repeating.items():
                system_name = data.get("System") or f"System {sec}"
                status = data.get("Normal/Abnormal") or "Normal"
                desc = data.get("Abnormal findings description") or ""
                audit_str = f"User: {data.get('_user', '')} | Date: {data.get('_date', '')}"
                input_str = f"{system_name}: {status}" + (f" - {desc}" if desc else "")
                alias = f"pe_{system_name.strip().lower().replace(' ', '_')}"
                yield {
                    **base,
                    "Field Label": system_name,
                    "Export Variable Name": alias,
                    "Data Input": input_str,
                    "Data Value": status,
                    "Audit Trails": audit_str,
                    "_EDC_SOURCE_ROW": data.get("_source_row", 0),
                }
                if desc and desc not in ("N/A", "None", ""):
                    clean_desc = desc.strip().lower().replace(" ", "_")[:50]
                    yield {
                        **base,
                        "Field Label": f"{system_name} - {desc}",
                        "Export Variable Name": f"{alias}_{clean_desc}",
                        "Data Input": desc,
                        "Data Value": desc,
                        "Audit Trails": audit_str,
                        "_EDC_SOURCE_ROW": data.get("_source_row", 0),
                    }
            block_rows = pe_non_repeating

        # Handle Antenatal PREGNANCY ASSESSMENT gestational age Weeks + Days
        if "PREGNANCY ASSESSMENT" in form.upper():
            weeks_row = next((r for r in block_rows if (r.get("Question Label") or "").strip().lower() == "weeks"), None)
            days_row = next((r for r in block_rows if (r.get("Question Label") or "").strip().lower() == "days"), None)
            if weeks_row and weeks_row.get("Value") and str(weeks_row.get("Value")).strip() not in ("N/A", "", "Flag: Unknown"):
                try:
                    w = float(weeks_row.get("Value"))
                    d = float(days_row.get("Value", 0)) if days_row and str(days_row.get("Value")).strip() not in ("N/A", "", "Flag: Unknown") else 0.0
                    total_ga = f"{(w + d / 7.0):.1f}"
                    yield {
                        **base,
                        "Field Label": "Ultrasound Gestational Age",
                        "Export Variable Name": "ga_weeks",
                        "Data Input": f"{int(w)} weeks {int(d)} days",
                        "Data Value": total_ga,
                        "Audit Trails": f"User: {weeks_row.get('User Name')} | Date: {weeks_row.get('Date & Time')}",
                        "_EDC_SOURCE_ROW": weeks_row.get("_EDC_SOURCE_ROW", 0),
                    }
                except (ValueError, TypeError):
                    pass

        # Handle DELIVERY OUTCOME gestational age Weeks + Days
        if "DELIVERY OUTCOME" in form.upper():
            weeks_row = next((r for r in block_rows if (r.get("Question Label") or "").strip().lower() == "weeks"), None)
            days_row = next((r for r in block_rows if (r.get("Question Label") or "").strip().lower() == "days"), None)
            if weeks_row and weeks_row.get("Value") and str(weeks_row.get("Value")).strip() not in ("N/A", "", "Flag: Unknown"):
                try:
                    w = float(weeks_row.get("Value"))
                    d = float(days_row.get("Value", 0)) if days_row and str(days_row.get("Value")).strip() not in ("N/A", "", "Flag: Unknown") else 0.0
                    total_ga = f"{(w + d / 7.0):.1f}"
                    yield {
                        **base,
                        "Field Label": "Gestational age at delivery",
                        "Export Variable Name": "ga_at_delivery",
                        "Data Input": f"{int(w)} weeks {int(d)} days",
                        "Data Value": total_ga,
                        "Audit Trails": f"User: {weeks_row.get('User Name')} | Date: {weeks_row.get('Date & Time')}",
                        "_EDC_SOURCE_ROW": weeks_row.get("_EDC_SOURCE_ROW", 0),
                    }
                except (ValueError, TypeError):
                    pass

        # Standard non-lab rows
        for r in block_rows:
            q = (r.get("Question Label") or "").strip()
            val = (r.get("Value") or "").strip()
            if not q or not val or val in ("N/A", "Flag: Unknown"):
                continue
            if ("DELIVERY OUTCOME" in form.upper() or "PREGNANCY ASSESSMENT" in form.upper()) and q.lower() in ("weeks", "days"):
                continue
            unit = r.get("Unit of Measure")
            unit_str = f" {unit}" if unit and unit != "N/A" else ""
            alias = q.lower().replace(" ", "_")
            audit_str = f"User: {r.get('User Name')} | Change: {r.get('Type of Change')} | Date: {r.get('Date & Time')}"
            yield {
                **base,
                "Field Label": q,
                "Export Variable Name": alias,
                "Data Input": f"{val}{unit_str}",
                "Data Value": val,
                "Audit Trails": audit_str,
                "_EDC_SOURCE_ROW": r.get("_EDC_SOURCE_ROW", 0),
            }

    for source_row, row in enumerate(rows, 2):
        row["_EDC_SOURCE_ROW"] = source_row
        subj = (row.get("Screening Number") or row.get("Subject Number") or row.get("Subject ID") or "").strip()
        visit = (row.get("Visit/Event Title") or "").strip()
        form = (row.get("Form Title") or "").strip()
        key = (subj, visit, form)
        if current_key is None:
            current_key = key
        if key != current_key:
            for item in flush_block(block):
                yield item
            block = []
            current_key = key
        block.append(row)

    if block:
        for item in flush_block(block):
            yield item
