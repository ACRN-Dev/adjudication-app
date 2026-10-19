"""Explicit authorization inventory for the retained RealTime API.

The inventory is intentionally exact: adding or removing a route requires a conscious
policy decision and a matching test change. This prevents an endpoint from inheriting
an accidental "authenticated user" default merely because it shares a router.
"""

MONITOR = "MONITOR_AUTHORITY"
ADJUDICATOR = "ADJUDICATOR_ASSIGNMENT_SCOPED"
WORKFLOW = "MONITOR_OR_ADJUDICATOR_SCOPED"


REALTIME_ROUTE_POLICIES = {
    ("POST", "/batches"): MONITOR,
    ("POST", "/batches/bulk"): MONITOR,
    ("GET", "/batches"): MONITOR,
    ("GET", "/batches/{batch_id}"): MONITOR,
    ("POST", "/batches/{batch_id}/cancel"): MONITOR,
    ("POST", "/batches/{batch_id}/retry"): MONITOR,
    ("POST", "/batches/{batch_id}/reprocess"): MONITOR,
    ("DELETE", "/batches/{batch_id}"): MONITOR,
    ("POST", "/batches/reset-demo"): MONITOR,
    ("GET", "/patients"): MONITOR,
    ("GET", "/patients/{participant_id}"): MONITOR,
    ("POST", "/patients/{participant_id}/approve"): MONITOR,
    ("POST", "/patients/{participant_id}/assign"): MONITOR,
    ("GET", "/assigned"): ADJUDICATOR,
    ("GET", "/assigned/{participant_id}"): ADJUDICATOR,
    ("POST", "/assigned/{participant_id}/queries"): ADJUDICATOR,
    ("POST", "/assigned/{participant_id}/recuse"): ADJUDICATOR,
    ("GET", "/queries"): MONITOR,
    ("POST", "/queries/{query_id}/resolve"): MONITOR,
    ("POST", "/observations/{observation_id}/corrections"): MONITOR,
    ("GET", "/corrections"): MONITOR,
    ("POST", "/corrections/{correction_id}/approve"): MONITOR,
    ("GET", "/progress"): WORKFLOW,
    ("GET", "/adjudicators"): MONITOR,
    ("POST", "/auto-assign"): MONITOR,
    ("GET", "/reference-ranges"): MONITOR,
    ("POST", "/reference-ranges"): MONITOR,
    ("POST", "/reference-ranges/{range_id}/deactivate"): MONITOR,
}
