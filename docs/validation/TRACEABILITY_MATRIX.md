# Requirements traceability matrix

Status meanings: `Repository-qualified` means automated evidence exists in this repository; `Implemented / external pending` means code/tooling exists but production-equivalent or independent execution is still required.

| Requirement | Design / implementation evidence | Verification evidence | Status |
|---|---|---|---|
| URS-AUTH-001/002 | `services/admin_security.py`, portal security dependencies, assignment authorization | `test_admin.py`, `test_realtime_security.py`, `test_retained_route_authorization.py` | Repository-qualified |
| URS-AUTH-003 | session MFA fields, full signature payloads, production runtime policy | signature, committee and runtime-policy suites | Implemented / external identity pending |
| URS-AUTH-004 | `services/runtime_policy.py`, demo-data scoping, production Admin routes | runtime-policy, auth-config, Admin tests | Repository-qualified |
| URS-AUTH-005 | `services/operational_controls.py`, auth audit | operational-controls and auth tests | Repository-qualified |
| URS-DATA-001 | realtime upload/pipeline policies, protected staging cleanup | upload, realtime, malware/security tests | Implemented / scanner service pending |
| URS-DATA-002 | durable import job dispatch, checksums and batch state | import durability/idempotency suites | Repository-qualified |
| URS-DATA-003 | prohibited mappings and restricted crosswalk | mapping/privacy/security suites | Repository-qualified; real extracts pending |
| URS-DATA-004 | canonical provenance, correction and supersession fields | mapping and correction-lineage tests | Repository-qualified |
| URS-DATA-005/006 | availability-state and visit-reconstruction services | readiness, missing-date, duplicate and narrative suites | Repository-qualified |
| URS-DATA-007 | controlled versions and approval gates | Admin version/governance tests | Repository-qualified |
| URS-DATA-008 | deterministic narrative services and human determination fields | narrative and lifecycle tests | Implemented / clinical approval pending |
| URS-WF-001 | monitor reconciliation and readiness APIs | monitor, realtime, scenario suites | Repository-qualified |
| URS-WF-002/003 | assigned-case APIs, visit completion and validation | authorization, visit and lifecycle suites | Repository-qualified |
| URS-WF-004/005 | signature receipts, payload hashes, immutable final state | signature, finalization and mutation-negative tests | Repository-qualified; compliance assessment pending |
| URS-WF-006/007 | workflow state machine, committee assignment/quorum/recusal | committee, chairperson, workflow suites | Repository-qualified |
| URS-WF-008 | export authorization and eTMF adapters with read-back receipts | export, finalization, adapter tamper tests; `qualify_etmf.py` | Implemented / live tenant pending |
| URS-GOV-001/002 | append-only Admin audit and independent approval checks | Admin and governance-control tests | Repository-qualified |
| URS-GOV-003 | access snapshot, decisions, revoke/modify, certification lock | `test_governance_controls.py` | Repository-qualified |
| URS-GOV-004/005/006 | retention policies, holds and disposition ledger | `test_governance_controls.py` | Repository-qualified; procedure approval pending |
| URS-OPS-001 | production runtime validation and deployment scripts | runtime-policy and deployment tests | Repository-qualified; target deployment pending |
| URS-OPS-002/003 | JSON request logs, metrics, correlation IDs, atomic rate counter | operational-controls tests | Repository-qualified; multi-replica PostgreSQL pending |
| URS-OPS-004 | `backup_restore.py` and DR runbook | `test_backup_restore.py` | Implemented / actual restore pending |
| URS-OPS-005 | migrations, deployment scripts, release gates | migration/deploy tests and validation plan | Implemented / approvals pending |
| URS-OPS-006 | semantic/focus/contrast/reduced-motion changes | managed Playwright + axe suite | Automated critical journeys pass; manual AT pending |
| URS-OPS-007 | `qualify_performance.py` and metrics | thresholded smoke/load/soak JSON | Implemented / target execution pending |

## Scenario coverage index

The backend suite covers normal longitudinal cases, chronic and gestational hypertension, proteinuric and organ-dysfunction evidence, severe-range findings, HELLP-supporting patterns, fetal evidence, delivery and postpartum workflows, missing visits/dates, duplicates, corrected/conflicting results, unknown and prohibited fields, disagreement, reviewer C, committee resolution, recusal, signature/lock, unauthorized access, and multi-participant imports. Final traceability requires QA to map each approved clinical expected result to the controlling protocol/rule version; repository tests alone cannot approve clinical truth.
