"""Deterministic participant import readiness evaluation.

Auto-approval rule (v2):
  A participant is ACCEPTED (auto-approved) when it has at least
  MIN_COMPLETE_VISITS complete visits (ACCEPTED or ACCEPTED_WITH_WARNINGS).
  Visits with HARD_QC_STATUSES are flagged and excluded from the count but
  no longer hard-reject the entire participant — real-world data almost
  always has at least one visit row with a hard status, which previously
  caused every upload to be rejected.

  Threshold: 4 ≤ complete_visits ≤ 6 (V01–V06 protocol window).
"""

EXPECTED_VISITS = tuple(f"V0{number}" for number in range(1, 7))
HARD_QC_STATUSES = {"EXCLUDED_MISSING_KEY_FIELDS", "DATE_CONFLICT_UNRESOLVED", "UNSAFE_ASSIGNMENT"}
WARNING_QC_STATUSES = {"MONITOR_QC_REQUIRED", "DATE_CONFLICT", "INFERRED_DATE", "MISSING_DATE"}

# Protocol visit window — participants need at least MIN_COMPLETE_VISITS
# usable visits to be eligible for auto-approval.
MIN_COMPLETE_VISITS = 4
MAX_COMPLETE_VISITS = 6


def _visit_evidence_count(visit):
    return sum(1 for observation in visit.observations if not observation.prohibited_flag and observation.canonical_variable)


def _visit_sort_key(visit):
    """Choose the best duplicate scheduled instance without letting sparse rows win."""
    has_date = 1 if visit.visit_datetime else 0
    evidence_count = _visit_evidence_count(visit)
    qc_rank = 0 if visit.qc_status in HARD_QC_STATUSES else (1 if visit.qc_status in WARNING_QC_STATUSES else 2)
    # Later source occurrence is a final deterministic tie-breaker only after
    # date, evidence and QC status have been considered.
    return (has_date, evidence_count, qc_rank, -(visit.visit_occurrence or 0))


def _best_scheduled_visits(participant):
    grouped = {code: [] for code in EXPECTED_VISITS}
    for visit in participant.visits:
        code = str(visit.scheduled_visit_code or "").upper()
        if code in grouped:
            grouped[code].append(visit)
    selected = {}
    superseded = {}
    for code, visits in grouped.items():
        if not visits:
            continue
        ordered = sorted(visits, key=_visit_sort_key, reverse=True)
        selected[code] = ordered[0]
        superseded[code] = ordered[1:]
    return selected, superseded


def participant_import_readiness(participant):
    """Evaluate import readiness using the 4–6 complete-visit auto-approval rule.

    A visit is *complete* when it is present in the source, has at least one
    mapped clinical observation, and is not hard-rejected (ACCEPTED or
    ACCEPTED_WITH_WARNINGS).  Visits with HARD_QC_STATUSES are recorded in the
    visit report as REJECTED for full auditability but are excluded from the
    complete-visit count rather than escalating to a participant-level hard
    rejection.  The participant is only hard-rejected when no V01–V06 visit
    block exists at all in the source export.
    """
    scheduled, superseded = _best_scheduled_visits(participant)
    hard_rejections = []
    warnings = []
    visit_report = []

    for code in EXPECTED_VISITS:
        visit = scheduled.get(code)
        if visit is None:
            visit_report.append({
                "visit": code,
                "status": "NOT_AVAILABLE",
                "accepted": True,
                "reason": "Scheduled visit not present in source export.",
            })
            continue

        evidence_count = _visit_evidence_count(visit)
        visit_warnings = []
        visit_hard_flags = []

        if not visit.visit_datetime:
            visit_warnings.append("Visit date is missing, but the scheduled visit is otherwise identifiable.")

        if evidence_count == 0:
            visit_report.append({
                "visit": code,
                "status": "NOT_AVAILABLE",
                "accepted": True,
                "reason": "Scheduled visit is present in source but contains no mapped clinical observations (e.g. not performed).",
            })
            continue

        # Hard-QC visits: flagged and excluded from the complete-visit count,
        # but they no longer hard-reject the entire participant.
        if visit.qc_status in HARD_QC_STATUSES:
            visit_hard_flags.append(
                f"Visit reconstruction status is {visit.qc_status} — excluded from complete-visit count."
            )
        elif visit.qc_status in WARNING_QC_STATUSES:
            visit_warnings.append(f"Visit reconstruction status is {visit.qc_status}.")

        if superseded.get(code):
            visit_warnings.append(f"{len(superseded[code])} duplicate scheduled instance(s) were superseded deterministically.")

        # Determine per-visit status.
        # A visit with HARD_QC_STATUS is REJECTED at visit level (audit trail)
        # but that does NOT escalate to a participant hard_rejection.
        if visit_hard_flags:
            # Promote hard flags to warnings at the participant level so the
            # monitor is informed, but do not block the whole participant.
            warnings.extend([f"{code}: {reason}" for reason in visit_hard_flags])
            visit_status = "REJECTED"
        elif visit_warnings:
            warnings.extend([f"{code}: {reason}" for reason in visit_warnings])
            visit_status = "ACCEPTED_WITH_WARNINGS"
        else:
            visit_status = "ACCEPTED"

        visit_report.append({
            "visit": code,
            "status": visit_status,
            # A hard-flagged visit is still *not accepted* at visit level, so
            # it is excluded from the complete-visit tally below.
            "accepted": visit_status in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"},
            "date": visit.visit_datetime.isoformat() if visit.visit_datetime else None,
            "mapped_fields": evidence_count,
            "warnings": visit_warnings + visit_hard_flags,
            "hard_rejection_reasons": visit_hard_flags,
            "reason": "; ".join(visit_hard_flags or visit_warnings) or "Mapped visit data is usable.",
        })

    # ── Participant-level gating ──────────────────────────────────────────────
    # Count usable visits: ACCEPTED or ACCEPTED_WITH_WARNINGS.
    complete_visits = sum(
        1 for item in visit_report
        if item["status"] in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"}
    )

    if not scheduled:
        # Truly nothing found — hard reject.
        hard_rejections.append("No V01-V06 visit block was found in the source export.")
    elif complete_visits < MIN_COMPLETE_VISITS:
        # Fewer than 4 complete visits: require Monitor review but do NOT
        # hard-reject so the record is still visible and assignable with sign-off.
        warnings.append(
            f"Only {complete_visits} of {MIN_COMPLETE_VISITS}–{MAX_COMPLETE_VISITS} "
            f"expected complete visits are usable. Monitor review required before assignment."
        )

    status = "REJECTED" if hard_rejections else ("ACCEPTED_WITH_WARNINGS" if warnings else "ACCEPTED")
    return {
        "status": status,
        "accepted": status in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"},
        "assignable": status in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"},
        "override_allowed": status == "ACCEPTED_WITH_WARNINGS",
        "missing_visits_pass": True,
        "present_visits": len(scheduled),
        "complete_visits": complete_visits,
        "min_complete_visits": MIN_COMPLETE_VISITS,
        "max_complete_visits": MAX_COMPLETE_VISITS,
        "accepted_visits": sum(1 for item in visit_report if item["status"] == "ACCEPTED"),
        "warning_visits": sum(1 for item in visit_report if item["status"] == "ACCEPTED_WITH_WARNINGS"),
        "rejected_visits": sum(1 for item in visit_report if item["status"] == "REJECTED"),
        "warnings": warnings,
        "hard_rejection_reasons": hard_rejections,
        "reasons": hard_rejections + warnings,
        "visits": visit_report,
    }
