"""Adapter from common wide EDC exports into the canonical long-form import contract."""
from services.realtime_mapping import DIRECT_ALIASES

EDC_ID_COLUMNS = ("SUBJID", "SubjectID", "USUBJID", "ParticipantID", "Screening #")
EDC_VISIT_COLUMNS = ("EVENT", "VISIT", "VISIT_NAME", "EventName", "Form Title")
EDC_DATE_COLUMNS = ("EVENT_DT", "VISIT_DATE", "VisitDate")


def is_edc_schema(fieldnames):
    names = {str(x or "").strip() for x in fieldnames or []}
    return bool(names.intersection(EDC_ID_COLUMNS)) and bool(names.intersection(EDC_VISIT_COLUMNS + EDC_DATE_COLUMNS))


def _first(row, columns):
    return next((str(row.get(c) or "").strip() for c in columns if str(row.get(c) or "").strip()), "")


def normalize_edc_rows(rows):
    """Yield RealTime-shaped rows. Empty clinical cells are retained as missing evidence.

    Rows without a subject key are excluded because they cannot safely be attached to
    a participant. Rows with a subject but missing visit/date are retained in an
    explicit EXCLUDED/UNSCHEDULED visit for Monitor QC rather than silently dropped.
    """
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

