"""Deterministic participant import readiness evaluation."""

EXPECTED_VISITS = tuple(f"V0{number}" for number in range(1, 7))


def participant_import_readiness(participant):
    """Evaluate import readiness; missing scheduled visits are acceptable by design."""
    scheduled = {
        str(visit.scheduled_visit_code or "").upper(): visit
        for visit in participant.visits
        if str(visit.scheduled_visit_code or "").upper() in EXPECTED_VISITS
    }
    rejected = []
    visit_report = []
    for code in EXPECTED_VISITS:
        visit = scheduled.get(code)
        if visit is None:
            visit_report.append({"visit": code, "status": "NOT_AVAILABLE", "accepted": True, "reason": "Scheduled visit not present in source export."})
            continue
        evidence_count = sum(1 for observation in visit.observations if not observation.prohibited_flag and observation.canonical_variable)
        reasons = []
        if not visit.visit_datetime:
            reasons.append("Visit date is missing.")
        if evidence_count == 0:
            reasons.append("No mapped clinical observations are present.")
        if visit.qc_status in {"EXCLUDED_MISSING_KEY_FIELDS", "DATE_CONFLICT"}:
            reasons.append(f"Visit reconstruction status is {visit.qc_status}.")
        accepted = not reasons
        if not accepted:
            rejected.extend([f"{code}: {reason}" for reason in reasons])
        visit_report.append({"visit": code, "status": "ACCEPTED" if accepted else "REJECTED", "accepted": accepted, "date": visit.visit_datetime.isoformat() if visit.visit_datetime else None, "mapped_fields": evidence_count, "reason": "; ".join(reasons) or "Mapped visit data is usable."})
    if not scheduled:
        rejected.append("No V01-V06 visit block was found in the source export.")
    return {
        "status": "ACCEPTED" if not rejected else "REJECTED",
        "accepted": not rejected,
        "missing_visits_pass": True,
        "present_visits": len(scheduled),
        "accepted_visits": sum(1 for item in visit_report if item["accepted"] and item["status"] == "ACCEPTED"),
        "rejected_visits": sum(1 for item in visit_report if not item["accepted"]),
        "reasons": rejected,
        "visits": visit_report,
    }
