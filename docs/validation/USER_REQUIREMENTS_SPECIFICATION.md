# User Requirements Specification (URS)

Document status: Draft for controlled review  
System: ACRN PROTECT-Africa Adjudication Platform  
Purpose: Define verifiable product requirements without replacing protocol, SOP, privacy, clinical, or regulatory approval.

## Authentication and authorization

| ID | Requirement | Acceptance criterion |
|---|---|---|
| URS-AUTH-001 | Every non-public API and portal shall require an authenticated active identity. | Anonymous and inactive identities receive 401/403 on every protected route. |
| URS-AUTH-002 | Authorization shall be enforced server-side by portal role, permission, study scope, and object assignment. | Horizontal and vertical access tests fail closed. |
| URS-AUTH-003 | Production shall use approved SSO, secure cookies, MFA assurance, and step-up authentication for signatures. | Production policy rejects missing configuration; signature receipt records session and MFA evidence. |
| URS-AUTH-004 | Demo identities and trusted demo headers shall be impossible in production. | Production startup fails when demo flags or unsafe routes are enabled. |
| URS-AUTH-005 | Authentication attempts shall be throttled with shared counters and audited without storing raw credentials or tokens. | Concurrent-node test shows no lost counter updates; audit contains outcome and actor/source reference. |

## Import, mapping, privacy, and provenance

| ID | Requirement | Acceptance criterion |
|---|---|---|
| URS-DATA-001 | Uploads shall enforce size, extension, content validation, malware scanning, and protected staging. | Invalid, oversized, infected, and mismatched files are rejected and audited. |
| URS-DATA-002 | Imports shall be durable, restart-safe, idempotent, and uniquely identified by checksum. | Duplicate submission does not create duplicate clinical records; pending work resumes after restart. |
| URS-DATA-003 | Direct identifiers, treatment allocation, and prohibited biomarkers shall never enter adjudicator-facing models or exports. | Negative privacy fixtures are rejected or classified restricted and absent from adjudicator responses. |
| URS-DATA-004 | Canonical observations shall preserve source file, row, field, form, visit, unit, mapping version, and correction lineage. | Every displayed material fact resolves to stored provenance; corrected values reference their predecessor. |
| URS-DATA-005 | Missing, unknown, not collected, not applicable, and negative shall remain distinct. | UI, narrative, PDF, and exports preserve each state without coercion to zero or normal. |
| URS-DATA-006 | Visit reconstruction shall retain complete evidence when duplicate or sparse rows occur and shall not require a date when a visit is otherwise identifiable. | Duplicate/missing-date qualification scenarios produce the approved visit packet. |
| URS-DATA-007 | Deterministic rules shall be versioned, tested, independently approved, and immutable after activation. | Activation is blocked without passing tests and required approvals. |
| URS-DATA-008 | Automated text shall describe evidence and rule output only; diagnosis, onset, severity, and certainty remain human determinations. | Narrative safety tests and clinical review find no unsupported diagnosis or reassurance. |

## Adjudication and committee workflow

| ID | Requirement | Acceptance criterion |
|---|---|---|
| URS-WF-001 | Monitor/QC shall control reconciliation, hard rejection, reasoned approval, and assignment readiness. | Hard failures cannot be overridden; every consequential action is audited. |
| URS-WF-002 | Reviewer A and B shall work independently and see only assigned, blinded records. | Cross-review and unassigned-object tests return 403/404 without leaking existence or content. |
| URS-WF-003 | Each visit and overall case shall require explicit completeness and required human determinations before signing. | Incomplete records cannot be signed or finalized. |
| URS-WF-004 | Electronic signatures shall bind identity, meaning, timestamp, full payload hash, authentication method, session, and MFA evidence. | Payload mutation invalidates verification; duplicate signing is idempotent or rejected. |
| URS-WF-005 | Signed/final records shall be immutable except through controlled supersession/reopen with preserved history. | UI and direct API mutation tests fail after lock; supersession retains both versions. |
| URS-WF-006 | Discordance shall route through reviewer C or committee according to the approved state machine, with independence, recusal, quorum, and stickiness controls. | Required disagreement scenarios follow only permitted transitions. |
| URS-WF-007 | Committee finalization shall require complete resolution content, meeting evidence, chair signature, and locking. | Missing quorum, rationale, meeting, or signature blocks finalization. |
| URS-WF-008 | Final exports and filing shall use only authorized finalized records and verify destination bytes by SHA-256 read-back receipt. | Tampering or missing destination receipt fails filing and release. |

## Governance, audit, and records management

| ID | Requirement | Acceptance criterion |
|---|---|---|
| URS-GOV-001 | Consequential events shall have append-only audit records with actor, role, timestamp, action, entity, before/after, reason, outcome, and integrity evidence. | Mutation/deletion is rejected and integrity verification detects tampering. |
| URS-GOV-002 | Administrative and clinical powers shall be separated; users cannot approve their own access, policy, or disposition request. | Self-approval tests return conflict/forbidden. |
| URS-GOV-003 | Periodic access review shall lock a hashed population snapshot, require a decision for every subject, apply revocation/modification, and become immutable on certification. | Incomplete review cannot close; completed review cannot change; revoked sessions stop working. |
| URS-GOV-004 | Retention policies shall be versioned and independently approved. | Draft creator cannot activate; prior active version is superseded. |
| URS-GOV-005 | Active legal holds shall block disposition at request, approval, and execution. | Matching/global hold yields a locked response at all three gates. |
| URS-GOV-006 | Disposition shall require elapsed retention, dual control, reason, execution reference, and evidence hash. | Premature, held, self-approved, or unverified requests cannot reach executed state. |

## Reliability, deployment, and usability

| ID | Requirement | Acceptance criterion |
|---|---|---|
| URS-OPS-001 | Production startup shall fail closed without PostgreSQL, required secrets, secure cookies, approved origins, metrics authentication, and non-demo settings. | Runtime policy test covers every prohibited configuration. |
| URS-OPS-002 | Every response shall have a correlation ID; structured logs and bounded Prometheus metrics shall support incident diagnosis without clinical content. | Route-template metrics and log review show no subject identifiers. |
| URS-OPS-003 | Critical writes shall use shared rate limits, transactions, unique constraints, and idempotency appropriate to concurrency. | Concurrent qualification shows no lost update or duplicate final record. |
| URS-OPS-004 | Encrypted backups shall have manifests and be restored into an isolated database on a scheduled basis. | Restore report verifies checksum, critical tables, audit fields, RTO, and RPO. |
| URS-OPS-005 | Releases shall use controlled migrations, rollback/runbooks, dependency scanning, and signed validation evidence. | Release gate rejects missing migration rehearsal, unresolved critical vulnerability, or unsigned validation. |
| URS-OPS-006 | Supported portals shall meet WCAG 2.2 A/AA for critical journeys and support keyboard/reduced-motion operation. | Automated scan has no violations and manual assistive-technology protocol passes. |
| URS-OPS-007 | Performance shall meet approved latency, error-rate, throughput, recovery, and soak thresholds on production-equivalent infrastructure. | Thresholded JSON evidence passes with PostgreSQL and multiple replicas. |

## Approval

This draft requires named Product Owner, Clinical Lead, Privacy/Security, QA/Validation, and System Owner approval before it becomes the controlled URS. Repository authorship is not approval.
