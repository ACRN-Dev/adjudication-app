# Full Remediation Implementation Plan

**System:** ACRN Adjudication application  
**Planning baseline:** `COMPREHENSIVE_READINESS_REPORT.md`, dated 2026-10-19  
**Starting readiness:** 23/75, or 31%  
**Current checkpoint:** 60/75, or 80.0%, after Tranche 6  
**Target:** validated production release with all Critical and High findings closed, all required controls evidenced, and no unaccepted safety-relevant Medium finding  
**Release posture:** live participant data and regulated adjudication remain prohibited until the final release gate is approved

## Implementation progress

**Tranche 1 completed on 2026-10-19:** production containment and the first clinical-data correction set are implemented and verified.

- Production now refuses SQLite fallback, demo flags, unsafe legacy-route enablement, and missing/invalid RealTime identity-protection keys.
- Legacy import, mapping, reconciliation, derivation, narrative, adjudication, committee, audit, and mock-workflow routers are not mounted in production. Legacy fabricated export routes additionally fail closed at request time.
- Unhandled API responses no longer return exception strings or tracebacks; callers receive a correlation ID.
- Longitudinal derivation now normalizes mapper variable names, keeps base/recheck BP series separate, pairs only source-correlated SBP/DBP observations, exposes an event date, and records unpaired evidence instead of position-pairing it.
- Backend rule engines now enforce the explicit 6-hour-to-1-week hypertension window, LDH greater than 600, baseline-creatinine doubling and oliguria, criterion-specific missingness text, and decision-support wording that requires adjudicator confirmation.
- Previously stale readiness and Reviewer C fixtures were corrected, and demo Monitor role handling now respects the provisioned portal role without test-order leakage.

Verification at this checkpoint:

- Backend: **388 passed, 0 failed**.
- Frontend service tests: **2 passed, 0 failed**.
- Production frontend build: passed; the existing large-bundle warning remains open under M-05.
- Repository database hashes remained unchanged.

This tranche contains C-01 and C-04 in production but does not replace them with the final authorized workflow. It materially remediates C-02 and the explicit rule defects in C-03, partially remediates C-06, H-06, H-09, H-11, and H-12, and leaves the remaining programme phases and formal validation gates open. The release posture therefore remains unchanged.

**Tranche 2 completed on 2026-10-19:** authorization boundaries on the retained RealTime workflow are materially strengthened.

- Batch upload, batch inventory, cancellation, reprocessing, Monitor participant inventory, approvals, assignments, roster access, auto-assignment, and reference-range administration now require provisioned Monitor/QC authority.
- Adjudicators can access only their assignment queue and assigned participant detail; Monitor inventory endpoints are denied to adjudicators and Chairpersons.
- Configured study scope is enforced before Monitor participant listing, detail, approval, assignment, auto-assignment, and progress access. Out-of-scope direct identifiers return not found.
- Reviewer queues and detail responses no longer disclose peer assignments. Reviewer progress exposes only the caller's identity, while Monitor/QC retains operational oversight.
- An exact method-and-path policy inventory now fails tests when any RealTime route is added without an explicit Monitor, adjudicator-assignment, or mixed scoped policy.

Verification at this checkpoint:

- Focused authorization suite: **18 passed, 0 failed**.
- Full backend suite outside the restricted temporary-directory sandbox: **393 passed, 0 failed**.
- `git diff --check`: passed.

This tranche advances C-01 and H-01 but does not close them. External identity-provider integration, rate-limit controls, detailed action/object policy coverage beyond the route-level guard, and independent security testing remain required. The release posture remains unchanged.

**Tranche 3 completed on 2026-10-19:** session, browser, retained-route, and raw-staging controls are implemented.

- Admin, Monitor, general API, and RealTime identities now use one server-side session resolver with a 30-minute sliding idle timeout and a 12-hour absolute lifetime by default.
- Password changes, administrative password resets, deactivation, role changes, portal-role changes, and study-scope changes immediately revoke active sessions.
- Production startup rejects insecure cookies, permissive SameSite settings, invalid session windows, non-HTTPS public URLs, and wildcard or non-HTTPS additional CORS origins.
- Cookie-authenticated production writes require the configured same origin. API responses receive no-store directives, CSP, frame denial, content-type protection, referrer and permissions policies; production responses receive HSTS.
- A deny-by-default test inventories every route retained in production and fails if it is neither explicitly public nor protected by a recognized authorization dependency. RealTime retains its stricter exact method-and-path policy inventory.
- Production deletes raw staged source files after processing and clears the persisted path. Cleanup failure becomes an audited blocking batch state rather than silently retaining source data.

Verification at this checkpoint:

- Affected multi-portal security suite: **131 passed, 0 failed**.
- Focused session, browser, staging, runtime-policy, and route-policy suite: **31 passed, 0 failed**.
- Full backend suite: **409 passed, 0 failed**.
- Frontend service tests: **2 passed, 0 failed**.
- Production frontend build: passed; the existing 1,246.77 kB main-bundle warning remains open.
- Repository database hashes remained unchanged and `git diff --check` passed.

This tranche materially advances C-01, C-06, H-01, H-08, and H-09. The remaining path to 75% cannot be achieved through security configuration alone: it requires one approved clinical rules service, canonical correction lineage, durable import workers, append-only audit, strong electronic signatures, governed workflow completion, qualified filing, operational qualification, accessibility work, and independent validation.

**Tranche 4 completed on 2026-10-19:** authoritative derivation, durable processing, audit integrity, governed reviewer workflow, and production signing are implemented.

- `services.clinical_derivation` is the single validated server boundary for DV execution. Persisted visit results carry `PROTECT-DV-2026.08`, the timeline exposes those exact results, and the reviewer client fails closed when an authoritative matching bundle is absent.
- RealTime imports are committed as database jobs before dispatch. Atomic leases, heartbeats, bounded retries, and startup recovery prevent request-process loss and concurrent duplicate execution.
- Longitudinal audit events use a sequence and previous-record hash. PostgreSQL advisory locking serializes writers and readiness verification detects sequence, link, or payload tampering.
- FORM-ADJ-09 queries and FORM-ADJ-08 recusals are persisted server workflows. Open queries block electronic signature; Monitor/QC closure requires a response and reason; recusal is prohibited after signing and transfers the stable role slot to an independent active reviewer with production contract enforcement.
- The adjudication router is retained in production behind authenticated adjudicator identity and assignment scope. The signed payload now covers the complete determination, visit, reviewer identity, signature meaning, and exact signing timestamp. Production signing requires a recent Entra MFA-authenticated session; the placeholder browser hash and default OTP were removed.
- Liveness is separated from readiness. Readiness returns 503 when the database, audit chain, or durable-job lease state is unsafe.

Verification at this checkpoint:

- Full backend suite outside the restricted filesystem sandbox: **417 passed, 0 failed**.
- Focused SSO/session/signature suite after signature hardening: **19 passed, 0 failed**.
- Production frontend build: passed; the 1,239.01 kB bundle warning remains open.
- `git diff --check`: required as the final tranche handoff check.

This tranche closes the implementation core of H-03, H-04, and H-05 and materially advances C-03, C-05, Monitor/QC, adjudicator workflow, reliability, deployment operations, and automated validation. The defensible score is **44/75 (59%)**, not 75%. The next threshold increment must complete governed correction/supersession, qualified external filing and reconciliation, live Admin/Owner operations, accessibility and browser E2E, backup/restore and observability evidence, and formal independent validation.

**Tranche 5 completed on 2026-10-19:** the repository implementation reaches the requested numeric threshold at **56/75 = 74.7%, reported as 75%**.

**Tranche 6 completed on 2026-10-19:** repository-addressable prerequisites for the 99% target are implemented, raising the evidence-based repository score to **60/75 = 80.0%**. This tranche includes observability/shared rate limits, backup/restore/DR tooling, compiled browser and WCAG automation, governed access reviews and records retention/legal holds, performance/soak and eTMF qualification runners, and the controlled-draft URS/risk/traceability/validation/release-gate set. The remaining 19 percentage points are not code backlog: they require production-equivalent PostgreSQL/multi-replica execution, live tenant integrations, restore/load/soak evidence, independent security/accessibility/compliance assessment, clinical UAT, and named approvals.

- Source corrections use immutable originals, linked replacement observations, independent approval, supersession-aware reviewer packets, and automatic participant re-derivation.
- Signed case and committee artifacts are read back from the configured destination and checksum-reconciled. Filing receipts and verification timestamps are persisted; mismatch, missing manifests, unsupported adapters, or filing errors fail closed. The local adapter is prohibited in production.
- Committee closure requires quorum, two signed independent reviews, concordance or a locked committee outcome, a full-payload chair signature, recent production MFA, and a verified report filing receipt.
- Production Admin queries and writes are separated from synthetic fixtures; denied/suspended access revokes live sessions, and administrative reports expose live record counts rather than a placeholder note.
- Portals, the workbench, and modals are code-split. The entry bundle is 205.48 kB, the largest feature chunk is 123.01 kB, and the prior >500 kB warning is eliminated. Skip navigation, visible focus, reduced-motion handling, and accessible loading states are present across portals.

Verification at this checkpoint:

- Backend unrestricted suite: **436 passed, 0 failed, 0 skipped**, followed by **8/8** focused governance and operational-control tests after the final scope and legal-hold changes.
- Frontend service tests: **2 passed, 0 failed**.
- Compiled-artifact Playwright suite: **13 passed, 0 failed**, including five portal WCAG A/AA scans.
- Production frontend build: passed with no oversized-chunk warning; both production and full dependency audits report zero known vulnerabilities.
- `git diff --check`: passed.

The numeric implementation target is met. Production authorization is still blocked on live Entra/eTMF qualification, independent clinical golden-set approval, PostgreSQL migration rehearsal, backup/restore and disaster-recovery evidence, penetration and WCAG testing, browser UAT, and controlled quality/regulatory approvals.

## 1. Delivery outcome

The remediation programme will replace the repository's parallel prototype paths with one authoritative, secure, traceable workflow:

1. A Monitor imports an approved CSV or XLSX source through quarantine and durable processing.
2. Every row receives a governed disposition and immutable source lineage.
3. Canonical observations preserve units, missingness, corrections, event correlation, and provenance.
4. One approved server-side clinical rules service produces versioned decision support.
5. Object-level authorization limits each user to the correct study, site, participant, assignment, and workflow phase.
6. Independent reviewers inspect the same locked evidence packet, raise governed queries or recuse, and sign through identity-provider step-up authentication.
7. Concordance and committee transitions follow one persisted state machine.
8. Signed decisions and audit events are append-only; changes create linked superseding versions.
9. Final artifacts and study exports are generated only from locked canonical records and are reconciled to verified eTMF receipts.
10. Production runs on PostgreSQL, encrypted object storage, durable workers, vault-managed keys, observable services, tested backup/restore, and controlled deployment.

The programme is complete only when implementation, migration, operational qualification, clinical validation, security testing, accessibility testing, and controlled documentation all pass. A functioning screen or passing unit test alone is not completion.

## 2. Planning assumptions

The sequence below assumes:

- two-week delivery increments;
- a stable cross-functional team of roughly 8-12 people: product owner, delivery lead/business analyst, two or three backend engineers, one or two frontend engineers, platform/SRE, QA automation/validation, security/identity support, clinical safety/medical monitor, and data-management representation;
- access to an approved identity provider, PostgreSQL environment, object storage, key vault, job queue, observability platform, and eTMF test tenant by Increment 3;
- sponsor decisions on clinical criteria and electronic-record/signature applicability are available within agreed decision SLAs;
- only synthetic or approved de-identified data is used until the production gate;
- the current prototype remains available as a reference but is not incrementally promoted to production while unsafe legacy routes remain active.

With those assumptions, the plan targets 12 increments, approximately 24 weeks, followed by an approval/cutover window. This is a planning model, not a commitment. Loss of clinical decision availability, external platform access, or dedicated validation capacity extends the critical path. A team below six dedicated implementers should re-estimate rather than compress validation.

## 3. Programme controls

### 3.1 Accountabilities

| Role | Accountable decisions and deliverables |
|---|---|
| Executive sponsor | Funding, production authorization, residual-risk acceptance |
| Product owner | Intended use, scope, role capabilities, backlog priority, acceptance |
| Clinical safety officer or medical monitor | Clinical rule specification, safety hazards, golden outcomes, clinical release sign-off |
| Data-management lead | Source contracts, mapping disposition, canonical dictionary, reconciliation, export acceptance |
| Security and privacy leads | Threat model, authorization, identity/signature design, DPIA, penetration-test closure |
| Engineering lead | Target architecture, technical quality, migration design, implementation integration |
| Platform/SRE lead | Environments, deployments, availability, backup/restore, telemetry, incident readiness |
| QA and validation lead | Requirements traceability, test independence, validation plan/evidence, release recommendation |
| Records/eTMF owner | Artifact templates, metadata, transfer/receipt controls, retention and retrieval |
| Release authority | Final review of evidence and go/no-go decision |

No engineer may approve their own safety-critical clinical requirement or independently waive a failed validation result. Clinical rules require clinical and data-management approval; authorization and signature controls require security/identity approval; final validation evidence requires QA approval.

### 3.2 Required registers

Create and control these from programme start:

- requirements and intended-use register;
- readiness-finding remediation register linking C-01 through L-04 to work items and evidence;
- clinical hazard and product risk register;
- architecture decision record register;
- route/permission/object-scope matrix;
- clinical rule decision log and requirements-to-test traceability matrix;
- source-field mapping and disposition register;
- data classification, retention, and lawful-processing register;
- validation deviations and defects register;
- dependency, SBOM, vulnerability, and exception register;
- environment/configuration and released-artifact register;
- residual-risk acceptance register.

### 3.3 Definition of ready

A work item may enter implementation only when it has:

- an approved requirement and safety/privacy classification;
- a named accountable owner and reviewer;
- explicit dependencies and data migration impact;
- acceptance criteria, negative cases, audit expectations, and rollback behaviour;
- UX states for loading, empty, error, conflict, unavailable, and retry where applicable;
- test-data requirements that exclude live participant data;
- documentation and operational impacts identified.

### 3.4 Definition of done

A safety-relevant work item is done only when:

- implementation and database changes are reviewed;
- unit, PostgreSQL integration, API authorization, and relevant browser tests pass;
- audit events and telemetry are verified;
- migrations are reversible by restore or approved forward repair and have been rehearsed;
- threat-model and clinical-hazard changes are reviewed;
- user and operator documentation is updated;
- traceability links requirement, code/change, tests, results, and defect closure;
- the accountable clinical, data, security, or operations owner accepts the evidence.

## 4. Delivery sequence and release gates

| Phase | Indicative increments | Primary result | Exit gate |
|---|---:|---|---|
| 0. Containment and control | 1 | Unsafe production paths disabled; programme governance established | Gate A: prototype safely contained |
| 1. Security and platform foundation | 2-4 | Deny-by-default access, production persistence, secure storage, durable work, unified audit | Gate B: secure foundation approved |
| 2. Clinical and canonical-data correction | 3-6 | One data contract, one approved rule engine, validated mapping/correction lineage | Gate C: clinical/data correctness approved |
| 3. Governed end-to-end workflow | 5-8 | Complete Monitor, reviewer, query, recusal, committee, signature, export, and eTMF path | Gate D: functional UAT candidate |
| 4. Product and operational completion | 7-10 | Production portals, accessibility, performance, observability, DR, documentation | Gate E: release candidate qualified |
| 5. Independent validation and cutover | 10-12 | Full validation, security testing, migration rehearsal, release evidence | Gate F: production authorization |

Phases overlap only where dependencies allow. Clinical-rule implementation may begin while platform work proceeds, but it cannot be integrated until the canonical data contract is approved. Portal completion must not create alternate authorization or derivation paths.

## 5. Workstream implementation plans

## 5.1 Programme containment and prototype isolation

**Findings:** C-01, C-04, C-06, H-09, H-10, M-02  
**Owner:** Engineering lead; approvals from security, clinical safety, and product  
**Target:** Increment 1

### Tasks

1. Build an environment capability matrix for demo, development, test, validation, staging, and production.
2. Introduce a fail-closed production profile. Production startup must refuse demo accounts, demo UI, demo data, SQLite, local eTMF fallback, external AI without approval, unsafe key defaults, and unclassified routes.
3. Remove or production-disable the legacy import, mapping, derive, narrative, adjudication, committee, audit, export, and mock workflow routers.
4. At the reverse proxy/API gateway, deny unsafe paths while code retirement proceeds.
5. Remove production navigation and links to simulated actions.
6. Add a prominent non-production banner and synthetic-data-only control in all non-production environments.
7. Inventory and rotate any previously shared non-demo credentials or keys using the approved secret process.
8. Create a route manifest test that fails when a new endpoint has no policy classification.

### Acceptance evidence

- Production configuration fails to start when any prohibited feature or fallback is enabled.
- Every known unsafe route returns not found or denied in a production-profile integration test.
- No demo row, fallback fact, static credential, or demo OTP can enter a production build, database, report, or export.
- The route manifest accounts for all endpoint declarations and is CI-enforced.
- Clinical safety and security jointly approve Gate A.

## 5.2 Identity, session, authorization, and object scope

**Findings:** C-01, C-05, H-01, H-09  
**Dependencies:** containment; identity-provider test tenant  
**Owner:** Security/identity lead with backend lead  
**Target:** Increments 2-4

### Design decisions

- Use the approved enterprise identity provider for authentication; do not retain application passwords for production users.
- Maintain a server-side session containing immutable user ID, current role grants, study/site scope, authentication context, MFA context, issuance, idle/absolute expiry, and revocation state.
- Centralize authorization as policies over action, role, study, site, participant, assignment, committee membership, workflow phase, account state, and environment.
- Scope database queries before materialization/serialization. Response filtering after broad queries is not sufficient.
- Never derive identity or authority from a submitted email/UPN, role, or reviewer parameter.

### Tasks

1. Approve the role and permission matrix for Admin, Owner, Monitor, Adjudicator A/B/C, Chairperson, auditor/read-only support, and service accounts.
2. Define segregation-of-duties conflicts and emergency-access procedures.
3. Integrate OIDC/SAML as approved; validate issuer, audience, nonce/state, signing keys, tenant, claims, clock skew, and logout.
4. Implement session rotation after authentication/privilege change, idle and absolute expiry, revocation, device/session inventory, and immediate deactivation propagation.
5. Implement CSRF protection for cookie-authenticated changes and secure-cookie requirements.
6. Create policy dependencies and object-scope query helpers; migrate every route.
7. Prevent reviewer identity disclosure before the authorized committee phase.
8. Add gateway/application rate limits for login, upload, query, export, signature, and administrative actions.
9. Add CSP, HSTS, framing, content-type, referrer, permissions, and cache-control policies at the deployment edge.
10. Replace traceback responses with stable error codes and correlation IDs; redact logs.

### Acceptance evidence

- Automated matrix covers every route for unauthenticated, deactivated, wrong-role, wrong-study/site, unassigned participant, wrong reviewer, inactive committee, and allowed scenarios.
- Attempts to forge a body/query identity never change effective authority.
- Reviewer A cannot view B/C identity or decision before the approved phase; Monitor cannot view prohibited in-flight clinical decisions.
- Session revocation and account deactivation take effect within the approved SLA.
- CSRF, session fixation, privilege-change, rate-limit, and redaction tests pass.
- Independent penetration testing finds no open Critical or High access-control issue.

## 5.3 Canonical clinical data and provenance

**Findings:** C-02, H-02, H-12, M-10  
**Dependencies:** clinical intended use; mapping source contracts  
**Owner:** Data-management lead and backend lead  
**Target:** Increments 2-5

### Canonical model requirements

Every clinical observation must carry:

- stable source system, import batch, source record/event, participant, visit, form, field, and occurrence identity;
- canonical variable and schema version;
- original and normalized value, original and canonical unit, conversion method/version;
- collection/event/result/effective timestamps with timezone and precision;
- explicit missingness and reason, never implicit zero/false;
- sensitivity/blinding classification;
- provenance pointer and source checksum;
- current, corrected, superseded, deleted-at-source, quarantined, or rejected status;
- supersedes/superseded-by links and correction reason;
- validation/QC status and approved disposition.

### Tasks

1. Approve the canonical data dictionary, naming rules, types, units, enumerations, missingness, sensitivity, and source precedence.
2. Replace string aliases with versioned typed identifiers shared by importer, database, rule service, API schema, and UI.
3. Correlate SBP and DBP through the same measurement/event identifier; reject or mark unpairable observations rather than position-pairing.
4. Model corrections and source deletions as immutable versions, not destructive updates.
5. Add database constraints for review-role separation, source/current-version uniqueness, workflow invariants, signature/artifact linkage, and missing foreign keys.
6. Use timezone-aware UTC storage with preserved source timezone/precision.
7. Implement transactional outbox events for every regulated state change.
8. Create a provenance API and reviewer-visible evidence trace without exposing restricted identity fields.
9. Build reconciliation between raw row counts, dispositions, canonical observations, visits, cases, and rejected/quarantined records.

### Acceptance evidence

- Golden tests prove no cross-event BP pairing and correct handling of out-of-order/repeated events.
- Corrected results supersede prior results without erasing history; derivation selects the approved current version.
- Unknown, not done, not applicable, not documented, and false/zero remain distinct through UI and export.
- Every displayed/derived value traces to source batch/record, mapping version, conversion, and correction history.
- Concurrent import/reprocess cannot create two current versions or break review-role constraints.

## 5.4 Clinical rules and decision-support service

**Findings:** C-03, H-12  
**Dependencies:** canonical data contract; approved clinical specification  
**Owner:** Clinical safety officer; engineering implementation owner; independent QA verifier  
**Target:** Increments 3-6

### Tasks

1. Convert the approved working instruction and protocol decisions into a controlled rule specification covering thresholds, inclusivity, units, time windows, gestational boundaries, source priority, missingness, ambiguity, query triggers, and escalation.
2. Resolve BP timing, one-week window, severe-range repeat rules, chronic hypertension, proteinuria units, renal baseline/oliguria, HELLP/partial HELLP, uteroplacental dysfunction, and near-34-week escalation.
3. Define stable rule IDs, rule-set version, protocol applicability, effective date, author/approver, formula, required inputs, output states, rationale template, and test vectors.
4. Implement one server-side pure rule service. Remove or make non-authoritative all duplicate Python and JavaScript engines.
5. Return `MET`, `NOT_MET`, `NOT_ASSESSABLE`, or `QUERY_REQUIRED` with evidence references; never output a final diagnosis or “confirmed” wording.
6. Persist the exact rule-set version and input observation version IDs with each derivation.
7. Implement controlled re-derivation: impact analysis, approval, batch execution, before/after reconciliation, and reviewer notification without rewriting signed history.
8. Make the frontend render server results and evidence, with clear separation between decision support and adjudicator judgment.

### Acceptance evidence

- Traceability covers every approved rule statement and boundary vector.
- Tests include 5:59/6:00-hour timing, seven-day boundary, 33+6/34+0, threshold-below/equal/above, baseline doubling, missing units, mixed timestamps, and conflicting evidence.
- Two independent clinicians/data reviewers approve blinded golden-case outputs.
- Browser and export show identical rule version, state, rationale, and evidence.
- Search/static checks show no executable alternate clinical rule authority.

## 5.5 Secure source ingestion and durable processing

**Findings:** C-06, H-02, H-05, H-08  
**Dependencies:** object storage, queue, key vault, canonical model  
**Owner:** Platform/SRE and backend leads  
**Target:** Increments 2-6

### Tasks

1. Accept approved CSV/XLSX templates through streaming upload into a private quarantine bucket.
2. Enforce maximum bytes, rows, columns, cells, archive expansion, processing time, and concurrent uploads.
3. Validate MIME/magic bytes, encoding, workbook structure, sheet/template/version, required fields, formulas/macros/external links, and safe filenames.
4. Integrate malware scanning; no parsing or downstream access before a clean result.
5. Require vault-provided independent pseudonym, encryption, and signing keys with key IDs; fail startup/import if missing.
6. Move processing to a durable queue and worker service with idempotency keys, job lease, heartbeat, checkpoints, cancellation, bounded retry, dead letter, and orphan recovery.
7. Make each stage explicit: received, quarantined, scanning, validated, mapping, reconstructing, deriving, reconciling, QC-ready, failed, cancelled, or superseded.
8. Implement import locking and safe reprocess using a new version; never delete the prior import lineage.
9. Implement encrypted staging retention and verified deletion, legal hold, backup exclusion/inclusion by policy, and storage-growth monitoring.
10. Produce a safe reject report with counts/codes and no raw sensitive values.

### Acceptance evidence

- CSV/XLSX golden fixtures and malicious/oversized/zip-bomb/macro/formula/encoding tests pass.
- Restart at every processing stage resumes or safely retries without duplicate canonical data.
- Duplicate upload, simultaneous reprocess, cancellation, and worker loss are deterministic.
- Missing or changed identity keys cannot create incompatible pseudonyms or unreadable crosswalk records.
- Quarantined/raw objects expire according to policy and deletion verification is auditable.

## 5.6 Mapping governance and source calibration

**Findings:** H-07, C-02  
**Dependencies:** canonical dictionary; approved source dictionaries  
**Owner:** Data-management lead with clinical reviewer  
**Target:** Increments 3-6

### Tasks

1. Load the Source 11 and Source 12 aggregate calibration results into the controlled disposition backlog.
2. Review all 274 and 349 distinct clinically plausible unmapped label/page pairs; record `MAP`, `PROHIBIT`, `RESTRICT_OPERATIONAL`, `RESTRICT_OUTCOME`, `INTERPRETATION_ONLY`, `NOT_RELEVANT`, or `QUERY_REQUIRED` with rationale and approvers.
3. Create source-system/study/form/version-specific mapping packages, including aliases, spelling variations, unit normalization, and effective dates.
4. Require two-person approval for changes affecting clinical evidence or blinding.
5. Version and sign mapping packages; do not edit an active version in place.
6. Provide impact preview before activation: affected rows, participants, observations, derivations, and signed cases.
7. Add mapping coverage and drift dashboards; alert on new/changed labels, units, forms, or unexplained unmapped growth.
8. Add rollback through version activation and governed reprocessing, retaining the prior output.

### Acceptance evidence

- No clinically plausible source pair remains without an approved disposition.
- Aggregate row-classification and canonical-variable counts match approved expectations for locked fixtures.
- Direct identifiers, prohibited biomarkers, outcomes, interpretations, and operational fields cannot enter reviewer clinical evidence through mapping changes.
- Mapping change, activation, impact, and reprocessing are fully audited and reproducible.

## 5.7 Audit trail and tamper evidence

**Findings:** H-03, C-05  
**Dependencies:** authorization identity; transactional outbox; production database  
**Owner:** Security and QA/validation leads  
**Target:** Increments 2-6

### Tasks

1. Define one audit envelope: event ID, event type/version, UTC time, actor/service/session, role and scope, action, entity/version, before/after digest or approved change set, reason, outcome, correlation/causation, source IP/device as permitted, and policy/rule/config version.
2. Publish the mandatory audit coverage catalog for access, search, view, import, mapping, QC, assignment, query, recusal, decision, signature, committee, export, eTMF, administration, authorization denial, and configuration change.
3. Write audit through a transactional outbox in the same commit as the regulated state change.
4. Deliver audit events to append-only/WORM storage with chained hashes or equivalent tamper-evident verification and trusted time.
5. Restrict audit search/export by scope and record access/export events.
6. Build daily gap, sequence, chain-integrity, delivery-lag, and clock-drift monitoring.
7. Define retention, legal hold, retrieval, and regulator/auditor export procedures.

### Acceptance evidence

- Fault injection between business commit and audit delivery does not lose the event.
- Modification/deletion/reordering/insertion is detected by integrity verification.
- Every mandatory action and denied attempt produces the approved event without raw secrets or unnecessary clinical data.
- An independent auditor can reconstruct a complete synthetic case chronology.

## 5.8 Electronic signature and immutable record versions

**Findings:** C-05, H-03, M-09  
**Dependencies:** identity step-up, canonical versioning, audit, artifact service  
**Owner:** Identity lead and records owner; clinical/QA approval  
**Target:** Increments 4-7

### Tasks

1. Complete the regulatory/electronic-signature applicability and risk assessment.
2. Define signing purpose, manifestation, meaning, permitted roles, re-authentication freshness, failure/retry, delegation prohibition, and correction/reopen policy.
3. Require a current server session, active assignment, correct workflow state, and identity-provider step-up MFA transaction bound to the signature challenge.
4. Canonicalize and hash the entire determination plus evidence snapshot IDs, rule/mapping/template versions, signer identity, purpose, and time.
5. Sign or seal using an approved server key/HSM process and preserve verification metadata.
6. Make the signed record append-only; any correction creates a linked superseding record with reason and new signature.
7. Generate the PDF/artifact from the signed snapshot and bind its digest to the signature record.
8. Display signer name/ID, role, date/time, meaning, version, and verification state on the artifact as approved.

### Acceptance evidence

- Changing any signed field, linked evidence/version, or artifact causes verification failure.
- A user cannot sign for another person, outside assignment, after deactivation, with stale MFA, or twice through retry.
- Concurrent submissions create at most one accepted signed version.
- Correction/reopen never mutates or hides the original signed version and is fully audited.

## 5.9 Governed case workflow, queries, recusal, and committee resolution

**Findings:** H-04, M-02, H-01, C-05  
**Dependencies:** authorization, canonical model, audit, signatures  
**Owner:** Product owner and clinical operations lead  
**Target:** Increments 5-8

### State-machine scope

Define explicit states and transitions for import QC, approval, assignment, evidence packet/version, review in progress, query open/answered/closed, recusal/reassignment, signed A/B reviews, concordance, discordance, Reviewer C, Chairperson/committee, finalized, export-ready, filed, corrected/superseded, and closed.

### Tasks

1. Replace mock/caller-controlled transitions with server-persisted commands and state preconditions.
2. Create evidence packet versions. Reviewers A and B must adjudicate the same approved snapshot unless a governed query creates a new version and both are notified/reset as required.
3. Implement clinical data queries with owner, category, rationale, evidence reference, status, response, attachment safety, timestamps, SLA, escalation, and resolution approval.
4. Implement recusal with reason, conflict classification, assignment release, capacity update, replacement selection, reviewer-blinding protections, and audit.
5. Enforce different reviewers and active contracts/capacity at database and service layers.
6. Define concordance across every decision field, not diagnosis alone.
7. Define when Reviewer C versus Chairperson/committee is required, including near-boundary cases, three-way divergence, unavailable reviewers, and conflicts.
8. Restrict comparison disclosure to the approved phase; lock the final committee rationale and source review adoption.
9. Implement controlled reopen/correction authorized by designated roles with impact notification and superseding versions.
10. Add server-side notifications and overdue escalation with delivery/retry evidence.

### Acceptance evidence

- Model-based tests reject every invalid transition and authorize every valid transition.
- A/B independence, identical evidence snapshot, query effects, recusal, capacity, Reviewer C, committee assignment, and lock behaviour pass concurrent tests.
- Browser local storage contains no clinical query or draft content beyond an approved encrypted/session design.
- A finalized case cannot change except through the approved superseding correction workflow.

## 5.10 Exports, PDF artifacts, and eTMF filing

**Findings:** C-04, C-05, M-09, L-01  
**Dependencies:** signed record versions, authorization, audit, object storage  
**Owner:** Records/eTMF and data-management leads  
**Target:** Increments 6-9

### Tasks

1. Delete or isolate all legacy/demo export implementations from production.
2. Define controlled export schemas, field sensitivity, inclusion criteria, ordering, encoding, missingness, provenance, version, and file naming.
3. Generate case artifacts only from signed/locked snapshots; never fill absent facts with defaults.
4. Escape CSV formula characters and validate PDF text/font/Unicode handling.
5. Add study/site/scope authorization, purpose/reason where required, row limits/streaming, and detailed export audit.
6. Implement eTMF transfer states: generated, transfer pending, sent, receipt received, checksum verified, filed, failed, retrying, reconciled.
7. Use an idempotency key and content digest so retry cannot create duplicate uncontrolled artifacts.
8. Reconcile local digest/metadata/count to the eTMF receipt; alert and block completion on mismatch.
9. Visually validate representative minimum, typical, maximum, multiline, missing-data, correction, and multilingual/special-character PDFs.
10. Test retrieval and verification after retention/restore.

### Acceptance evidence

- Unknown/unfinalized records fail closed; synthetic rows cannot enter a non-demo export.
- Export totals and hashes reconcile to eligible locked versions.
- Authorization and confidentiality tests cover every output field and role.
- PDF visual approval and CSV consumer/schema validation are signed.
- UI says “filed” only after a verified eTMF receipt; retry and outage scenarios preserve one authoritative artifact.

## 5.11 Database, migrations, and data remediation

**Findings:** H-06, M-10  
**Dependencies:** target data model; production PostgreSQL  
**Owner:** Database/platform lead  
**Target:** Increments 2-8

### Tasks

1. Remove application-import `create_all`, schema mutation, demo seeding, and PostgreSQL-to-SQLite fallback in production.
2. Adopt one migration framework with immutable revisions, checksums, dependency graph, database lock, transaction strategy, and applied-version ledger.
3. Establish production-like baseline schema from a clean database and from an upgrade copy.
4. Add all approved foreign keys, checks, unique/partial indexes, immutable/version constraints, and query indexes.
5. Write preflight checks for capacity, locks, invalid legacy rows, duplicate assignments/current observations, orphan records, and incompatible enum/data values.
6. Create remediation scripts that report before changing, write audit/reconciliation output, are idempotent, and operate on approved backups.
7. Define backup/restore rather than unsafe down migration as the rollback for destructive transformations.
8. Compare full schema objects—not only columns—after every migration.
9. Rehearse clean install, each supported upgrade path, failed migration recovery, point-in-time restore, and forward repair.

### Acceptance evidence

- Production refuses SQLite and refuses pending/failed migration state.
- Fresh and upgraded databases have identical approved schemas.
- Migration rerun is deterministic; concurrent startup cannot apply twice.
- Data remediation preserves counts, lineage, signatures, and audit history, with signed reconciliation.
- Restore meets approved RPO/RTO and application integrity checks.

## 5.12 Admin, Owner, Monitor, reviewer, and Chairperson product completion

**Findings:** M-01, M-03  
**Dependencies:** authoritative backend workflows and policies  
**Owner:** Product owner with frontend/backend leads  
**Target:** Increments 6-9

### Tasks

1. Approve the minimum production capability set for each role; remove everything not supported.
2. Replace hard-coded dashboard values with defined metrics, calculation version, source, timestamp, scope, and empty/error states.
3. Complete only authorized Admin controls: user lifecycle, roles/scopes, approved configuration/version activation, access reviews, audit access, and system health.
4. Complete Owner oversight only after separation-of-duties and clinical-data access are approved.
5. Make Monitor views operationally complete without exposing prohibited reviewer content.
6. Make reviewer/Chairperson screens display authoritative evidence/version/state and reject stale writes.
7. Add server-side draft/version handling where permitted, unsaved-change guards, optimistic concurrency, conflict resolution, idempotent submit, and retry status.
8. Standardize loading, empty, filtered-empty, unauthorized, forbidden, unavailable, validation-error, conflict, offline, and server-error views.
9. Remove browser alerts/confirmations for governed actions; use accessible dialogs with explicit outcomes and server receipts.

### Acceptance evidence

- No production screen contains simulated actions, hard-coded metrics, or unsupported claims.
- Role-based E2E journeys pass through the same APIs/policies as direct API tests.
- Errors never appear as empty success states; stale edits cannot overwrite a newer record.
- Product and representative users approve UAT for each enabled role.

## 5.13 Accessibility and responsive usability

**Findings:** M-03, M-04  
**Dependencies:** stable workflow UI  
**Owner:** Frontend lead and accessibility specialist  
**Target:** Increments 7-10

### Tasks

1. Adopt WCAG 2.2 AA and document supported browsers, devices, viewport sizes, zoom, assistive technologies, and language requirements.
2. Implement semantic landmarks/headings/tables/forms, programmatic labels/instructions, error summaries, and status announcements.
3. Implement accessible modal focus entry/trap/Escape/return, non-modal alternatives where appropriate, and no keyboard traps.
4. Verify colour contrast, non-colour cues, target size, reduced motion, 200-400% zoom/reflow, and responsive evidence tables.
5. Preserve focus and context after validation, query response, signing, and state transitions.
6. Add axe checks to components and browser journeys, without treating automation as manual conformance.
7. Conduct keyboard-only and screen-reader testing with adjudicators/operations users.

### Acceptance evidence

- No open WCAG A/AA defect in release scope unless formally assessed and approved before release; safety-critical form defects are non-waivable.
- Supported browser/device matrix and manual assistive-technology scripts pass.
- Signature, clinical evidence, query, error recovery, and timeout journeys are independently verified.

## 5.14 Performance, resilience, and frontend optimization

**Findings:** H-05, M-05  
**Dependencies:** durable workers, production-like infrastructure  
**Owner:** Platform/SRE and engineering leads  
**Target:** Increments 7-10

### Tasks

1. Agree service-level objectives and workload envelope: users, participants, visits, observations, file sizes, concurrent imports, queries, signatures, and exports.
2. Add bounded pagination and filtering, stable ordering, query-count budgets, and maximum export scopes.
3. Profile database plans and add evidence-based indexes; remove N+1 and excessive materialization.
4. Add route-level frontend code splitting, lazy portal loading, dependency review, cache strategy, and bundle budgets.
5. Stream large import/export processing; cap memory, CPU, time, and concurrent worker use.
6. Test retry storms, queue backlog, database unavailability, object-storage/eTMF timeouts, network latency, worker termination, and partial external failures.
7. Run baseline, target, stress, soak, and recovery tests with synthetic maximum datasets.

### Acceptance evidence

- Approved p95/p99 UI/API/job targets and error rates are met at target load with headroom.
- No data loss, duplicate commit, or uncontrolled retry occurs during fault injection.
- Bundle and per-route budgets pass; initial role portal loads only necessary code.
- Capacity model, scaling limits, and alert thresholds are documented and tested.

## 5.15 Operations, observability, security supply chain, and disaster recovery

**Findings:** M-06, M-07, L-03, L-04  
**Dependencies:** target services/infrastructure  
**Owner:** Platform/SRE and security leads  
**Target:** Increments 2-10

### Tasks

1. Provision isolated development, test, validation, staging, and production through reviewed infrastructure as code.
2. Use least-privilege service identities, private networking, TLS, egress allow-lists, encrypted storage, WAF/API limits, and controlled administrative access.
3. Implement liveness, readiness, startup, and dependency health checks; readiness must fail for wrong database, missing key, pending migration, or unavailable mandatory dependency.
4. Add structured redacted logs, metrics, traces, dashboards, and alerts for requests, authorization denials, job stage/age/failure, mapping drift, audit gaps, signatures, exports/eTMF, database/storage, and SLO burn.
5. Define alert owners, severities, escalation, paging, maintenance, and evidence retention.
6. Create encrypted backups and point-in-time recovery for database, identity crosswalk, object artifacts, configuration metadata, and audit according to policy.
7. Write and exercise incident, breach, key compromise, data correction, failed deployment, queue backlog, external-service outage, restore, and regional disaster runbooks.
8. Generate Python/Node/container SBOMs; pin/hash dependencies; run SAST, SCA, secret, license, IaC, and image scans.
9. Produce signed build provenance and immutable image promotion; prohibit rebuilds between validation and production.
10. Eliminate owned-code warnings and add lint/type/static checks as release gates.

### Acceptance evidence

- Alerts fire and route correctly during controlled exercises.
- Backup restore and disaster exercise meet RPO/RTO and pass clinical/audit integrity reconciliation.
- Release has no unapproved Critical/High vulnerability and meets remediation SLAs for lower severities.
- Production image digest, SBOM, source revision, migrations, configuration, and validation results are linked.

## 5.16 Documentation, training, validation, and quality-system evidence

**Findings:** H-11, M-08 and all validation gaps  
**Dependencies:** progressive; final evidence depends on feature freeze  
**Owner:** QA/validation lead  
**Target:** Increments 1-12

### Tasks

1. Approve intended use, user requirements, system requirements, architecture, data flows, trust boundaries, risk assessment, and validation plan before design freeze.
2. Keep bidirectional traceability between requirements, hazards/findings, design decisions, implementation changes, tests, defects, and released artifacts.
3. Repair test isolation and stale fixtures; require the complete backend suite to pass repeatedly and in randomized order.
4. Add PostgreSQL integration, mapping golden, authorization matrix, state-machine, signature/tamper, browser E2E, accessibility, performance/resilience, migration/restore, and operational qualification suites.
5. Establish production-like synthetic validation data with approved expected results and immutable checksums.
6. Create controlled SOPs and runbooks for user/access management, import/QC, mapping/rule change, query/recusal/reassignment, signing, committee, correction/reopen, export/eTMF, backup/restore, incident, and change/release management.
7. Train each role and verify competency before provisioning production access.
8. Run formal system integration testing, operational qualification, performance qualification as applicable, clinical/data UAT, security testing, accessibility testing, and validation summary.
9. Reconcile every deviation and defect; retest fixes and assess regression/validation impact.
10. Establish periodic access review, audit review, backup restore, vulnerability, mapping drift, rule review, vendor review, and post-release surveillance schedules.

### Acceptance evidence

- Complete automated suites pass on the immutable release candidate in the validation environment.
- No open Critical/High finding or validation defect; any residual Medium risk has a named accountable approver, rationale, compensating control, expiry, and remediation date.
- Validation summary confirms requirements and intended use with no unexplained trace gaps.
- Training, SOP effective dates, support/on-call readiness, and production access approvals precede cutover.

## 6. Findings-to-workstream traceability

| Finding | Primary workstream | Closure gate |
|---|---|---|
| C-01 | Identity, authorization, containment | B |
| C-02 | Canonical data, mapping | C |
| C-03 | Clinical rules | C |
| C-04 | Export/artifact, containment | D |
| C-05 | Signature, identity, workflow | D |
| C-06 | Secure ingestion, secrets/storage | B |
| H-01 | Authorization/object scope | B |
| H-02 | Canonical correction lineage, import | C |
| H-03 | Unified audit | B |
| H-04 | Governed case workflow | D |
| H-05 | Durable processing/resilience | D |
| H-06 | Database/migrations | B |
| H-07 | Mapping governance | C |
| H-08 | Secure ingestion | B |
| H-09 | Secure error handling/observability | B |
| H-10 | AI governance or removal | C |
| H-11 | Validation/test repair | F |
| H-12 | Canonical missingness/clinical wording | C |
| M-01 | Portal completion | D |
| M-02 | Workflow state machine | D |
| M-03 | Frontend state/draft safety | E |
| M-04 | Accessibility | E |
| M-05 | Performance | E |
| M-06 | Operations/DR | E |
| M-07 | Supply chain | E |
| M-08 | Controlled documentation | F |
| M-09 | Artifact/eTMF lifecycle | D |
| M-10 | Data/time/contracts/constraints | C |
| L-01 | Artifact generation | D |
| L-02 | Static quality gates | E |
| L-03 | Health/readiness | B |
| L-04 | Warning elimination | E |

## 7. Increment-level delivery plan

### Increment 1 — Contain and govern

- Establish registers, accountabilities, validation strategy, and intended-use draft.
- Disable unsafe routes/features under production profile and gateway controls.
- Freeze clinical rules, mappings, signatures, and exports for production promotion.
- Repair immediate test-environment isolation sufficient to create a reliable baseline.
- Approve target architecture and vendor/environment procurement.

**Gate A:** production profile cannot reach known prototype bypasses; no live data allowed.

### Increment 2 — Platform and policy skeleton

- Establish PostgreSQL-only configuration, migration framework, object quarantine, queue/worker skeleton, vault integration, and infrastructure as code.
- Approve route/role/object matrix and canonical data model draft.
- Implement unified error contract, health separation, logging redaction, and audit envelope/outbox foundation.

### Increment 3 — Authorization and canonical ingestion

- Integrate identity-provider sessions and centralized policies.
- Implement source identity/event/version model, typed canonical identifiers, missingness, and provenance.
- Implement streaming quarantine and safe CSV/XLSX validation.
- Complete sponsor decisions for clinical-rule ambiguities.

### Increment 4 — Durable import, audit, and clinical engine core

- Implement durable import state machine, checkpoints, retries, and reconciliation.
- Implement append-only audit delivery/integrity checks.
- Implement the approved server rule service and boundary tests.
- Add database invariants and migration rehearsals.

**Gate B:** authorization, storage/keys, database, ingestion perimeter, and audit foundation independently reviewed.

### Increment 5 — Mapping and correction completeness

- Complete source-field dispositions and versioned mapping activation.
- Implement correction/supersession and safe reprocessing.
- Integrate canonical observations with the rule service and evidence trace.
- Begin workflow state-machine and evidence packet implementation.

### Increment 6 — Clinical/data validation and reviewer workflow

- Complete clinical golden cases and independent review.
- Complete Monitor QC/approval/assignment and reviewer evidence/determination flow on one authoritative path.
- Remove duplicate rule engines and legacy exports from production packages.

**Gate C:** clinical and data owners approve golden end-to-end results and mapping coverage.

### Increment 7 — Query, recusal, signature, and committee

- Implement governed query/response, recusal/reassignment, evidence packet versioning, signature challenge, and immutable decision versions.
- Implement concordance, Reviewer C, near-boundary escalation, and Chairperson state transitions.
- Begin controlled PDF/export and eTMF transfer.

### Increment 8 — Finalization and data migration rehearsal

- Complete artifact signing/digests, final export, eTMF receipt/reconciliation, correction/reopen, and notification/escalation.
- Rehearse legacy-data assessment and migration/remediation on a synthetic or approved masked copy.
- Execute role-based end-to-end tests.

**Gate D:** product/clinical operations accept the complete governed workflow as a UAT candidate.

### Increment 9 — Production portal and accessibility completion

- Complete approved Admin/Owner/Monitor/reviewer/Chairperson scope.
- Remove all simulations and hard-coded metrics.
- Complete safe drafts, errors, concurrency, responsive layout, and accessibility remediation.

### Increment 10 — Capacity, resilience, operations, and feature freeze

- Run performance, soak, fault-injection, backup/restore, DR, monitoring/alert, and security supply-chain qualification.
- Complete controlled documents, SOPs, runbooks, and training material.
- Freeze requirements and release-candidate functionality; only defect fixes after freeze.

**Gate E:** release candidate meets technical, accessibility, operational, and documentation entry criteria for formal validation.

### Increment 11 — Formal independent validation

- Execute system/operational qualification, clinical/data UAT, authorization/security, accessibility, performance, migration, restore, and eTMF scripts on the immutable candidate.
- Triage deviations by safety and validation impact; retest approved fixes.
- Conduct independent penetration test and final privacy/security review.

### Increment 12 — Release evidence and cutover rehearsal

- Close findings and defects; reconcile requirements/risks/tests/evidence.
- Rehearse production deployment, migration, smoke tests, rollback/restore, and communications.
- Complete training/competency and provision just-in-time production access.
- Prepare validation summary, residual-risk record, and go/no-go pack.

**Gate F:** release authority approves the exact image, configuration, migrations, data plan, and operating model.

## 8. Data migration and legacy-record strategy

The prototype database must not be assumed suitable for direct migration. First classify every existing environment and record set as synthetic, test, pilot/non-regulated, or potentially regulated.

### Migration rules

- Purge synthetic/demo records from any target intended for production; retain them only in isolated demo/test environments.
- Never infer missing clinical facts while transforming legacy records.
- Records without verifiable provenance, rule version, assignment, signature, or audit lineage must be quarantined for manual disposition, not silently upgraded to “valid.”
- Preserve original record snapshots and identifiers in restricted, access-controlled migration archives where retention is required.
- Convert records through versioned, idempotent migration jobs with row-level status and reason.
- Recompute decision support only under the approved new rules and retain old outputs as historical, explicitly non-authoritative versions.
- Do not convert prototype password/OTP signatures into compliant electronic signatures. Require authorized re-review/re-signing or classify records as legacy noncompliant according to sponsor/QA decision.

### Reconciliation

For each migration run, reconcile:

- source, eligible, migrated, quarantined, rejected, and duplicate counts;
- participants, visits, observations, corrections, assignments, reviews, decisions, artifacts, audit events, and identity-crosswalk records;
- aggregate statuses and study/site scopes;
- pre/post checksums and referential-integrity results;
- signed-record and artifact verification;
- unresolved exceptions with named owners and dispositions.

Migration approval requires data management, QA/validation, privacy/security for identity data, and clinical ownership where an outcome or evidence packet changes.

## 9. Test and validation matrix

| Layer | Minimum release evidence |
|---|---|
| Unit | Canonical conversion, mapping, clinical boundaries, state transitions, policies, signature canonicalization, export encoding |
| Property/fuzz | No cross-event pairing, idempotency, parser robustness, state-machine invariants, authorization input manipulation |
| PostgreSQL integration | Constraints, transactions, locks, migrations, outbox, job checkpoints, correction/version selection |
| API contract | Versioned request/response/errors, authentication, role/object scope, pagination/limits, stale writes |
| Mapping golden | Approved CSV/XLSX fixtures to dispositions, observations, visits, issues, derivations, reconciliation |
| Browser E2E | Complete role journeys, independent review, query, recusal, committee, signature, correction, export, error/retry |
| Accessibility | axe plus keyboard, screen reader, zoom/reflow, contrast, modal, error, timeout, responsive testing |
| Security | SAST/SCA/SBOM/secrets/IaC/container, CSRF/session, upload abuse, DAST, penetration, audit tamper |
| Performance/resilience | Target/stress/soak, maximum files, concurrent work, worker/process loss, dependency outage, retry/backlog recovery |
| Operations | Clean install, upgrade, failed migration, rollback/restore, key rotation, backup/DR, alert/incident drills |
| Clinical/data UAT | Sponsor-approved cases, missing/ambiguous/corrected data, boundary cases, artifact/export verification |

All tests must record environment, code/image digest, configuration version, database schema revision, fixture checksum, execution time, result, evidence location, defects, and approver where required.

## 10. CI/CD release gates

### Pull-request gate

- formatting, lint, type checks, owned-code warning policy;
- unit/property/component tests;
- migration static checks;
- secret, dependency, license, SAST, and IaC scan;
- route-policy and clinical-rule duplication checks;
- changed-requirement/risk/test trace links for regulated scope.

### Main/integration gate

- clean PostgreSQL migration and upgrade tests;
- full backend/frontend suites in deterministic and randomized order;
- authorization matrix and API contracts;
- mapping golden and browser E2E;
- container build, SBOM, image scan, provenance signing;
- no Critical/High vulnerability or failed safety-critical test.

### Release-candidate gate

- immutable image deployed to validation using production-equivalent configuration;
- feature freeze and approved migration bundle;
- performance/resilience, accessibility, security, restore/DR, eTMF, and UAT evidence;
- all requirements/risks/findings traced and all deviations dispositioned;
- validation summary and release-authority approval.

Production must promote the validated image digest; rebuilding from the same source is not equivalent.

## 11. Cutover and rollback plan

### Pre-cutover

- confirm Gate F approvals, change ticket, maintenance window, communications, support/on-call coverage, and escalation contacts;
- verify target infrastructure, keys, certificates, IdP/eTMF connectivity, migration revision, capacity, dashboards, and alert routing;
- take and verify protected backups; record recovery point and restore location;
- freeze legacy writes and exports at the agreed time;
- run preflight reconciliation and stop on any unexplained difference.

### Cutover

1. Deploy the validated immutable image and configuration.
2. Apply the approved migration under a database advisory lock.
3. Execute data conversion/quarantine and signed reconciliation.
4. Start workers, then API, then frontend; keep external traffic blocked.
5. Run technical smoke tests, authorization probes, synthetic clinical golden check, audit delivery check, and eTMF test transaction as approved.
6. Obtain engineering, QA, security, clinical/data, and operations release confirmations.
7. Open traffic gradually with enhanced monitoring and restricted initial user cohort.

### Rollback or recovery triggers

- failed migration or reconciliation;
- authorization/blinding failure;
- clinical golden result mismatch;
- audit event loss/integrity failure;
- signature verification failure;
- unavailable mandatory persistence, key, queue, or artifact dependency;
- error/latency/data-quality thresholds exceeding approved limits.

Rollback must use the rehearsed deployment rollback plus point-in-time restore where schema/data changes cannot safely reverse. Do not partially roll back application code while retaining an incompatible schema. All rollback decisions and post-event reconciliation are audited.

## 12. Operational handover and post-release monitoring

Before handover, operations must demonstrate:

- dashboards and alerts for availability, latency, error rates, queue age, imports, mapping drift, rejected/quarantined data, audit delivery/integrity, authorization denials, signature/export/eTMF failures, database/storage capacity, backup age, and certificate/key expiry;
- runbooks for every alert and dependency outage;
- access-controlled support tooling that does not bypass blinding or clinical locks;
- daily reconciliation for initial release, then risk-based cadence after stability review;
- vulnerability, access, audit, backup restore, vendor, mapping, clinical-rule, retention, and business-continuity review schedules;
- post-release clinical safety surveillance and rapid disable/rollback capability for a defective rule or mapping version.

Conduct hypercare after cutover with daily cross-functional review. Exit hypercare only after the agreed stability period, no unexplained reconciliation variance, no open safety/security incident, acceptable SLOs, completed user feedback triage, and release-authority approval.

## 13. Key programme risks and mitigations

| Risk | Effect | Mitigation and trigger |
|---|---|---|
| Clinical decisions remain unresolved | Rule engine and golden validation stall | Decision log with named medical owner and SLA; unresolved safety rule blocks Gate C |
| Legacy/prototype paths survive | Bypass of new controls | Production package allow-list, route manifest, gateway deny, negative tests |
| Identity/eTMF/vendor environments arrive late | Critical-path integration delay | Contract and sandbox provisioning in Increment 1; simulator only for development, never release evidence |
| Existing data lacks provenance/signature validity | Migration cannot preserve regulated status | Early inventory; quarantine/manual re-review; no inferred upgrade |
| Team tries to preserve all demo screens | Scope growth and alternate paths | Approve minimum production capability; remove unsupported features |
| Test count grows but evidence remains weak | False confidence | Risk-based traceability, golden outcomes, negative/fault tests, independent validation |
| Mapping changes alter signed cases | Endpoint inconsistency | Versioned impact analysis, no mutation, controlled re-derivation and superseding review |
| Audit or job infrastructure is treated as eventual polish | Integrity gaps persist | Make outbox/queue/storage Gate B dependencies, not post-MVP work |
| Performance work starts too late | Architecture rework | Define workload/SLOs early; run representative tests from Increment 4 |
| Release schedule pressures residual-risk waivers | Unsafe production authorization | Critical/High issues non-waivable; independent QA and release authority |

## 14. First 30 days

The first two weeks should deliver containment and decision infrastructure, not feature work:

- appoint accountable owners and release authority;
- approve non-production status and prevent live data use;
- create finding, requirement, risk, decision, route-policy, mapping, and traceability registers;
- disable/gateway-block legacy unsafe routes in production profile;
- freeze clinical rule/mapping/export promotion;
- inventory environments, users, data, secrets, databases, artifacts, and external integrations;
- begin identity, storage, queue, PostgreSQL, vault, observability, and eTMF test-environment provisioning;
- repair test state isolation and establish a reproducible baseline command/output archive;
- hold clinical/data workshops to resolve the rule and canonical-data decisions.

By day 30, the programme should have:

- approved intended-use and target architecture drafts;
- a complete route/role/object authorization matrix;
- an approved canonical-data model and clinical decision backlog;
- an environment and migration strategy;
- working production-profile fail-closed checks;
- a prioritized implementation backlog linked to every readiness finding;
- validation plan, synthetic-data plan, and Gate A approval;
- confirmed external dependency dates and a re-estimated 24-week delivery forecast.

If any of those foundations are absent at day 30, do not compensate by starting more portal features; replan the critical path.

## 15. Final production authorization checklist

The release authority should approve production only when all answers are yes:

- [ ] Are C-01 through C-06 and H-01 through H-12 closed with accepted evidence?
- [ ] Is every production endpoint authenticated, explicitly authorized, object-scoped, and tested?
- [ ] Is there one approved canonical contract, mapping package, and clinical rule engine?
- [ ] Do source-to-artifact golden cases match clinician/data-approved expected results?
- [ ] Are signatures genuine step-up transactions bound to immutable complete record versions?
- [ ] Are audit events complete, append-only, tamper evident, monitored, and retrievable?
- [ ] Are imports quarantined, scanned, bounded, encrypted, durable, restart safe, and reconciled?
- [ ] Are demo, synthetic, fallback, mock, and fabricated paths absent from production?
- [ ] Are PostgreSQL migrations, data conversion, backup/restore, rollback, and DR rehearsed?
- [ ] Are final artifacts/exports authorized, provenance-complete, visually validated, and eTMF-reconciled?
- [ ] Are browser journeys usable, concurrency safe, responsive, and WCAG 2.2 AA validated?
- [ ] Are performance, resilience, security, privacy, and supply-chain criteria met?
- [ ] Is the complete automated suite green on the immutable release candidate?
- [ ] Are UAT, validation summary, SOPs, training, support, monitoring, and access approvals complete?
- [ ] Are all residual Medium/Low risks documented with owners, controls, expiry, and acceptance?
- [ ] Is the exact image digest/configuration/migration bundle approved for cutover?

Any “no” keeps the system out of production.
