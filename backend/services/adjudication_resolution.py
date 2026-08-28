"""Single source of truth for visit concordance and adopted determinations."""
from datetime import datetime
from models.canonical import AdjudicationStatus, ReviewerRole


def clinical_signature(record):
    """Fields that must agree before two determinations are clinically concordant."""
    return (
        record.meets_criteria, record.diagnosis, record.onset_class,
        record.severity, record.certainty, record.date_of_diagnosis,
    )


def resolve_visit(visit, records):
    signed = {r.reviewer_role: r for r in records if r.signed}
    a, b, c = (signed.get(x) for x in (ReviewerRole.REVIEWER_A, ReviewerRole.REVIEWER_B, ReviewerRole.REVIEWER_C))
    if not a or not b:
        return "IN_REVIEW", None, None
    if clinical_signature(a) == clinical_signature(b):
        return "CONCORDANT", a, "A_B_CONCORDANT"
    if not c:
        return "AWAITING_REVIEWER_C", None, "A_B_DISCORDANT"
    if clinical_signature(c) == clinical_signature(a):
        return "RESOLVED_BY_MAJORITY", a, "C_WITH_A"
    if clinical_signature(c) == clinical_signature(b):
        return "RESOLVED_BY_MAJORITY", b, "C_WITH_B"
    return "FINALIZED", c, "REVIEWER_C_FINAL"


def apply_visit_resolution(participant, visit, records):
    status, adopted, resolution = resolve_visit(visit, records)
    visit.status = status
    visit.resolution_type = resolution
    visit.final_record_id = adopted.id if adopted else None
    visit.finalized_at = datetime.utcnow() if adopted else None
    visit.filing_status = "PENDING" if adopted else "NOT_READY"
    # Participant state is a roll-up; never let one visit hide another open visit.
    statuses = [v.status for v in participant.visits]
    if any(s == "AWAITING_REVIEWER_C" for s in statuses):
        participant.status = AdjudicationStatus.COMMITTEE_PENDING
    elif any(s == "IN_REVIEW" for s in statuses):
        participant.status = AdjudicationStatus.IN_REVIEW
    elif all(s in {"CONCORDANT", "RESOLVED_BY_MAJORITY", "FINALIZED"} for s in statuses):
        participant.status = AdjudicationStatus.FINALIZED
    return status, adopted, resolution
