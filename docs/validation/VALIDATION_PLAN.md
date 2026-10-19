# Validation plan

Document status: Draft for QA approval. This plan supplies executable protocols and evidence locations; it does not claim independent validation or regulatory approval.

## Roles and independence

- System Owner approves intended use, environment, and release decision.
- Clinical Lead approves clinical rules, expected outcomes, narratives, and residual clinical risk.
- QA/Validation owns protocol approval, witness requirements, deviations, and final report.
- Security/Privacy approves threat model, privacy classification, penetration test, and residual security risk.
- Records Owner approves retention, legal hold, backup, restore, and disposition procedures.
- Test executors must not approve their own evidence where independence is required.

## Controlled baseline

Record repository commit, dirty-worktree diff, dependency locks, migration inventory, environment variables with secrets redacted, container/image digests, operating system, browser versions, PostgreSQL version, external integration configuration versions, rule/mapping/form/workflow versions, and approved test-data hashes.

## Installation qualification (IQ)

1. Deploy the exact baseline to isolated validation infrastructure through the production deployment path.
2. Confirm PostgreSQL is mandatory; demo accounts/data, local filing, unsafe routes, and insecure cookies are rejected.
3. Apply migrations to a production-like copy, verify schema, restart every service, and execute rollback/recovery rehearsal.
4. Verify TLS, origins, secrets provider, identity configuration, object storage, malware scanner, monitoring, alert routing, backup schedule, time synchronization, and least-privilege service accounts.
5. Archive command output, redacted configuration, database schema fingerprint, and approver signatures.

## Operational qualification (OQ)

Execute the full automated backend suite, frontend service tests, production build, managed browser suite, axe suite, dependency scanning, SAST/secret scan, migration tests, backup verification, restore rehearsal, performance smoke/load/soak, concurrency, and integration contract checks. Each result must identify command, environment, pass/fail/skip counts, warnings, duration, and output hash.

Negative OQ must include anonymous, wrong-role, wrong-study, wrong-object, inactive identity, self-approval, signature tamper, post-lock mutation, prohibited fields, infected/oversized/malformed uploads, duplicate submission, stale workflow state, missing quorum, legal hold, premature disposition, destination tamper, database outage, worker interruption, retry exhaustion, and rate-limit exhaustion.

## Performance qualification

Follow `docs/operations/PERFORMANCE_AND_INTEGRATION_QUALIFICATION.md`. Run with PostgreSQL and at least two replicas. Approved protocol values supersede runner defaults. Collect application, database, host, queue, and storage telemetry. Averages cannot conceal p95/p99 or sustained growth.

## Performance qualification (PQ) / user acceptance

Named Monitor, Adjudicator A/B/C, Chairperson, Admin, Owner, Clinical Lead, and Records Owner execute realistic end-to-end journeys using approved pseudonymized data. Reconcile every portal, PDF, CSV, audit event, and eTMF receipt to source and expected results. Include desktop, tablet, keyboard-only, screen reader, zoom/reflow, long content, error recovery, refresh, session expiry, and concurrent-user journeys.

The clinical PQ dataset must cover all 25 scenarios listed in the readiness mission, with expected results approved before execution. Test authors must not derive expected clinical truth from the code under test.

## Security and privacy qualification

Perform independent threat-model review and penetration testing, including IDOR, privilege escalation, session/CSRF/CORS, SSO claims, upload polyglots, injection, dependency exposure, log leakage, pseudonymization, crosswalk isolation, export access, and cloud storage permissions. Verify prohibited data against representative real source schemas under controlled access.

## Disaster recovery and continuity

Create an encrypted backup, validate its manifest, restore into an isolated PostgreSQL database, run critical integrity tests, measure RPO/RTO, and perform an application read-only smoke test against the restored database. Test database, application-node, worker, integration, and storage outages plus rollback to the previous application release.

## Deviations and evidence

Every failure creates a deviation with identifier, expected/actual result, evidence, impact assessment, root cause, correction, retest, and approvals. Never overwrite original evidence. Evidence is timestamped, hashed, access controlled, and linked from the traceability matrix.

## Acceptance

Release requires: all P0/P1 requirements passed; no open Critical/High defect; all critical risks accepted by accountable owners; complete URS-to-test traceability; successful PostgreSQL migration/restore/load/soak; live integration qualification; independent security and accessibility results; clinical UAT approval; and a signed validation summary report. Conditional approval must be explicit, time-bound, and cannot waive privacy, blinding, record integrity, signature, or clinical-safety controls.
