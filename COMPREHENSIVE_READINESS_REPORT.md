# Comprehensive Production-Readiness Assessment

**Repository:** ACRN Adjudication application  
**Assessment date:** 2026-10-19 (Africa/Johannesburg)  
**Assessment basis:** repository commit `670b231`, the current working tree, and remediation Tranches 1 through 6 completed on 2026-10-19  
**Decision:** **NOT READY for live clinical, regulated, or production use**  
**Current readiness score:** **60/75 = 80.0%**  
**Original baseline:** **23/75 = 30.7%, reported as 31%**

## Current remediation checkpoint

Six implementation tranches raise repository readiness from **31% to 80%**, a gain of **37 points out of 75**. Tranche 6 adds production observability and shared atomic rate limits; backup/restore/DR tooling; managed compiled-artifact browser and axe qualification; governed access-review, retention, legal-hold and disposition workflows; load/soak and live eTMF qualification runners; and controlled URS, risk, traceability, validation and release-gate documents. This score measures repository implementation and local verification. It is not authorization for live clinical or regulated use because target-environment qualification and independent approvals remain open.

Sections below that describe the original assessment are retained as historical evidence. This checkpoint and the current traceability/validation documents supersede historical statements that browser tests, retention controls, backup tooling, observability, or controlled requirements are absent.

| Category | Baseline /5 | Current /5 | Basis for change |
|---|---:|---:|---|
| Clinical-rule correctness | 1 | 4 | One versioned server boundary validates every persisted DV result, the browser fails closed, and approved corrections trigger re-derivation. Clinical approval and an independent golden validation set remain open. |
| Mapping and data integrity | 1 | 4 | Canonical-name handling, source-correlated BP pairing, immutable originals, independently approved replacements, supersession lineage, reviewer-packet filtering, and automatic re-derivation are implemented. Full source-catalog disposition remains open. |
| Privacy and blinding | 2 | 4 | Production identity-protection secrets fail closed, prohibited fields remain excluded, raw staged uploads are deleted after processing, and governed retention/legal holds now block disposition. Independent privacy qualification and target storage evidence remain open. |
| Authentication and authorization | 1 | 4 | Unsafe legacy routers are unavailable in production. Retained routes are deny-by-default tested; RealTime access enforces role, study, and assignment scope; peer identity is withheld; sessions enforce idle and absolute expiry and revoke on privilege changes; cookie writes require same origin. Identity-provider tenant qualification and independent penetration testing remain open. |
| Monitor/QC workflow | 2 | 4 | Imports are durable and recoverable; Monitor/QC manages governed queries and independent source-correction approvals with automatic re-derivation. Broader usability validation remains open. |
| Adjudicator workflow | 2 | 4 | Assigned reviewers use server-derived evidence, persisted queries, enforced signing holds, and governed recusal with independent replacement. Draft recovery and formal usability validation remain open. |
| Committee/Chairperson workflow | 2 | 4 | Production uses the authenticated retained path; quorum, signed-review prerequisites, locked outcomes, full-payload signatures, recent MFA, and verified report filing are enforced before closure. Formal UAT remains open. |
| Admin/Owner governance | 1 | 4 | Production records are separated from demo fixtures; access reviews use hashed snapshots, complete decisions, revocation and immutable certification; retention policies require independent approval; legal holds block disposition. Owner operational UAT remains open. |
| Audit and electronic signatures | 1 | 4 | Longitudinal audit events are hash chained with PostgreSQL serialization and verification. Signatures bind the full determination, meaning, user, visit, session, and time; production requires recent Entra MFA. External Part 11 assessment and database immutability controls remain open. |
| Exports and eTMF records | 1 | 4 | Legacy fabricated exports fail closed; signed case and committee artifacts are read back, checksum-reconciled, receipt-persisted, audited, and blocked from `FILED`/closure on mismatch. Live eTMF tenant qualification remains open. |
| Reliability and performance | 1 | 4 | Durable leased imports are restart-safe, and role portals/workbench/modals are code-split. The entry bundle fell from 1,239.01 kB to 205.48 kB and the >500 kB warning was removed. Load, soak, and multi-node recovery remain open. |
| Deployment and operations | 2 | 4 | Production rejects unsafe configuration and fallback storage; migrations cover the new controls; separate liveness and fail-closed database/audit/job readiness endpoints now support orchestration. Backup/restore, telemetry, alerting, and DR qualification remain open. |
| Automated testing and validation | 2 | 4 | Backend verification is 436/436, frontend service tests are 2/2, the compiled browser suite is 13/13, builds pass, and dependency audit is clean. Production-equivalent performance, security and regulated validation remain open. |
| Accessibility and usability | 2 | 4 | Five portal landing pages pass automated WCAG A/AA scans; keyboard bypass, focus, accessible names/regions, contrast and reduced motion are tested. Independent manual WCAG/assistive-technology and role UAT remain open. |
| Documentation and governance | 2 | 4 | Controlled-draft URS, risk register, traceability matrix, validation plan, release gates, DR and performance/integration protocols now exist. Named approval and execution remain open. |
| **Total** | **23/75** | **60/75** | **80.0%; all repository-addressable 99% prerequisites were implemented or supplied as executable protocols, but external evidence still blocks release.** |

Verification for this checkpoint:

- Backend: **436 passed, 0 failed, 0 skipped** in the final unrestricted suite (170.76 seconds; deprecation warnings remain), followed by **8/8** focused governance and operational-control tests after the final scope and legal-hold changes.
- Frontend service tests: **2 passed, 0 failed**.
- Compiled-artifact Playwright suite: **13 passed, 0 failed**, including five automated portal WCAG A/AA scans.
- Production frontend build: passed; the entry bundle is approximately **205.48 kB**, the largest feature chunk is **123.01 kB**, and the prior over-500 kB warning is gone.
- `npm audit` and `npm audit --omit=dev`: **0 known vulnerabilities**.
- A local performance smoke attempt did not yield evidence because the temporary service did not become ready inside the orchestration timeout; no performance pass is claimed.
- `git diff --check`: passed.

## 1. Executive decision

This application is a substantial, test-backed prototype, not a production-ready clinical adjudication system. It has a coherent React/FastAPI/PostgreSQL architecture, role-oriented portals, a useful longitudinal import model, deterministic derivation support, reviewer separation concepts, committee workflows, signed artifact generation, and meaningful automated test coverage. Several implementation choices are notably sound: production deployment disables demo accounts and demo UI, the newer final-release exports are authenticated and audited, import readiness prevents a fully absent scheduled-visit set from assignment, warning overrides require Monitor rationale, prohibited fields are excluded from canonical mapping, and npm reports no known production dependency vulnerabilities.

The baseline identified six release-blocking Critical findings: unauthenticated clinical and administrative APIs; loss or incorrect pairing of mapped observations; inconsistent clinical engines; fabricated legacy exports; weak signature binding; and unsafe identity staging and secret fallbacks. The first tranche contains the unsafe legacy surface in production, corrects the confirmed observation-assembly defect and explicit backend rule discrepancies, and makes production identity secrets fail closed. These findings are not all closed: the retained workflow still needs universal object-level authorization, one clinically approved rules engine, strong electronic signatures, protected source storage, and independent validation. The application therefore still requires a controlled redesign and validation cycle rather than release.

The original 31% and current 80% are transparent arithmetic scores, not estimated probabilities of safety. Fifteen equally weighted categories are scored from 0 to 5. A category receives 5 only when production controls have approved target-environment evidence; 4 represents a strong repository implementation with external qualification or approval still open; 3 represents a materially usable implementation with important gaps; 1 represents prototype behaviour with a release blocker; 0 means absent. Incomplete independent and target-environment validation caps the decision at **Not ready**, regardless of the numeric score.

## 2. Scope, method, and evidence integrity

The review covered all visible application layers and operational material: 362 repository files, including 294 reviewable code/configuration/documentation files, 175 Python files, 26 JSX files, 22 SQL files, 56 test-related files, and 121 declared FastAPI routes. The assessment traced the browser portals through API dependencies, persistence models, derivation services, exports, deployment scripts, migrations, and tests. It also compared the implemented clinical rules with the approved working instruction at `Supporting resources/EOPE_Adjudication_Working_Instruction.pdf` and calibrated both supplied RealTime conversions using the repository's own mapping classifier.

Baseline verification performed:

- Backend suite: **361 collected; 347 passed; 14 failed; 2,031 warnings** in 165.72 seconds.
- One eTMF adapter failure was confirmed as a restricted temporary-directory artefact and passed when rerun outside the sandbox. The remaining full-suite result still contains **13 non-environmental failures**.
- Three Monitor failures passed in isolation, demonstrating order-dependent state leakage rather than a consistently broken Monitor feature.
- Frontend production build passed outside the restricted process sandbox. The main JavaScript bundle is 1,246.77 kB (274.02 kB gzip), with Vite's over-500 kB warning.
- Frontend service tests: **2 passed, 0 failed**.
- `npm audit --omit=dev`: **0 known vulnerabilities** across 7 production and 119 total packages.
- Python dependency vulnerability scanning was not available in the repository environment; this is recorded as a validation gap, not treated as a clean result.
- Repository database files were hashed before and after executable verification and did not change.
- No application code, database, configuration, or source data was modified by this assessment. This report is the only intended new file.

The working tree already contained modifications to `backend/main.py` and `backend/tests/test_admin.py` before the assessment. They were preserved and treated as part of the assessed state. No secret values, patient identifiers, or source-row contents are reproduced here.

Limitations:

- Browser E2E was not run because the existing Playwright suite requires separately started, stateful demo services and has no managed `webServer` lifecycle. Static inspection and lower-layer execution were used instead.
- No live Entra tenant, eTMF/SharePoint endpoint, LIMS/EDC connector, production PostgreSQL service, SMTP service, secret vault, backup target, or observability backend was available. Claims about those integrations therefore require future integration qualification.
- PDF creation tests passed, but representative long-form clinical artifacts were not visually approved against controlled templates in this review.
- Calibration used the supplied converted CSVs because the production importer itself does not accept XLSX.

## 3. Architecture and end-to-end workflow assessment

The product is a Vite/React single-page application backed by FastAPI and SQLAlchemy. It has Admin, Monitor/QC, Adjudicator, Chairperson, and Owner views. The backend contains both legacy clinical models/routes and a newer longitudinal RealTime pipeline. PostgreSQL is intended for production; SQLite is used for development/demo and can be selected silently after a PostgreSQL connection failure. Import processing runs as an in-process FastAPI background task. Clinical derivation is duplicated across at least two Python engines and JavaScript equivalents.

The intended flow is understandable:

1. Monitor uploads a source export.
2. Rows are classified, prohibited/direct-identity fields are separated, canonical observations and visits are reconstructed, and derived variables are calculated.
3. Monitor reviews issues/readiness, configures ranges, approves, and assigns two independent reviewers.
4. Reviewers inspect the longitudinal case, complete a determination, and sign it.
5. Concordant cases finalize; discordance routes to an additional reviewer or Chairperson/committee workflow.
6. A locked artifact is generated and may be transferred to a local or eTMF adapter; final study exports are produced.

The repository does not enforce that flow consistently. Legacy endpoints bypass the newer gates, several workflow actions are browser-only simulations, and authorization differs by router. This creates parallel paths where a user—or an unauthenticated caller—can read, mutate, or export records without the controls presented in the UI.

### Portal-by-portal outcome

| Portal/workflow | What is present | Production assessment |
|---|---|---|
| Admin | User/role management, health, many governance screens, audit/report simulations | Production build exposes only a narrow subset; numerous actions and metrics remain demo/simulated. Authorization is stronger in the Admin router, but the system-wide API surface defeats portal separation. |
| Monitor/QC | RealTime upload, mapping/QC, reference ranges, readiness, assignment, progress | The most complete operational portal. Readiness rationale and capacity/contract concepts are good. Any authenticated role can still reach broad patient/batch endpoints, import is not durable, raw identity handling is unsafe, and correction/supersession is incomplete. |
| Adjudicator | Assigned queue, longitudinal evidence, DV display, narrative, decision/signature | Useful workbench, but clinical derivations can be wrong or inconsistent. Assignment enforcement has gaps, the signature is not genuine step-up authentication, queries/recusal are not controlled backend workflows, and UI errors can appear as empty queues. |
| Chairperson/committee | Protected Chairperson routes and decision UI; comparison/lock concepts | The newer Chairperson API checks active assignment. A separate legacy committee router is unauthenticated and can disclose both reviews or lock outcomes, invalidating the control boundary. |
| Owner | Oversight dashboard, determinations, metrics, audit-oriented UI | Disabled in production and populated substantially with hard-coded values. It is not a production feature. |
| Import/mapping | Preamble/header detection, versioned classifier, blinding exclusions, checksums, visit reconstruction | CSV only; no durable job system, size/content scanning, correction semantics, or complete mapping coverage. A case-building defect disconnects mapped variables from clinical derivation. |
| Reconciliation/derivation | Multiple rule engines, missingness concepts, trace-like evidence structures | Engines disagree with each other and with the approved instruction. The system can both miss true criteria and generate unsupported confirmations. |
| Signing/finalization/export | Signature fields, artifact generation, local/eTMF adapter, protected final-study export | Legacy exports remain unsafe and unprotected. Signature identity/integrity is insufficient. eTMF fallback and artifact lifecycle need qualification and fail-closed behaviour. |

## 4. Findings register

All findings below are confirmed from repository evidence unless explicitly labelled a validation gap. “Correction” is the minimum remediation; “Addition” is the control or evidence needed to make the correction durable.

### Critical findings — 6

#### C-01 — Clinical data, decisions, audit history, imports, and legacy exports lack universal authentication/authorization

**Classification:** Finding — access control / privacy / record integrity.  
**Evidence:** `backend/main.py:121-174` claims and registers the routers, but dependencies are not applied globally. Unauthenticated routes include import (`backend/api/import_api.py:59-65,157-163,259-260`), mapping (`backend/api/mapping.py:39,60`), derive (`backend/api/derive.py:39-40`), narrative read/generate/edit (`backend/api/narrative.py:224-225,319-324,363-364`), adjudication submit/read (`backend/api/adjudication.py:702-706,742-747,844-848`), committee queue/Reviewer C/lock (`backend/api/committee.py:64-65,104-105,288-289`), audit retrieval (`backend/api/audit.py:14-35`), and legacy export (`backend/api/export.py:54-55,110-111,155-160`). The committee queue returns reviewer identities and rationales at `backend/api/committee.py:79-98`.  
**Impact:** An unauthenticated caller can discover clinical/audit data and invoke integrity-changing workflows, including adjudication and committee finalization. UI role separation provides no protection against direct API calls.  
**Root cause:** Authorization is implemented per route in newer modules while legacy routers remain mounted. No deny-by-default router policy or endpoint authorization inventory is enforced in CI.  
**Correction:** Immediately disable legacy routers in every non-demo environment. Apply authentication at router/application scope, then require explicit least-privilege policy for every endpoint and object-level scope for study, site, participant, assignment, and committee membership. Bind every write to the authenticated principal; never accept authority from body/query identity fields.  
**Addition/acceptance evidence:** Machine-readable route-policy matrix; automated unauthenticated, horizontal, vertical, inactive-user, out-of-study, and unassigned-case tests for all 121 routes; API gateway deny rules; security review showing zero unclassified endpoints.

#### C-02 — Mapped source evidence is lost or misassembled before derivation

**Classification:** Finding — clinical data integrity.  
**Evidence:** The mapper emits lowercase canonical names, while `backend/services/longitudinal_derivation.py:6-19` creates uppercase aliases but `:21-27` tests the original observation value against uppercase names. BP systolic and diastolic observations are collected independently and paired by list position at `:28-33`, not by visit/time/source identity. Generated readings expose `datetime`, while the active DV hypertension logic examines `date` at `backend/services/dv_engine.py:141-166`. The derived onset depends on the resulting hypertension/proteinuria/organ flags at `backend/services/longitudinal_derivation.py:46-50`.  
**Impact:** RealTime data can be silently excluded, unrelated BP values can be paired, and qualifying non-severe hypertension can be marked not assessable or absent. This can change trigger, onset, severity, reviewer presentation, and final outcome.  
**Root cause:** Canonical schema contracts are implicit strings rather than typed/versioned objects; observation correlation keys are discarded; there is no end-to-end golden-case test from raw row to displayed and exported determination.  
**Correction:** Introduce one canonical observation contract with normalized names at ingestion. Correlate SBP/DBP by source row or measurement/event identifier and timestamp. Preserve provenance through the case builder. Make unknown/unpairable values explicitly not assessable; never position-pair them.  
**Addition/acceptance evidence:** Golden datasets covering normal, severe, missing, repeated, corrected, and out-of-order observations; property tests proving no cross-event pairing; trace from every displayed criterion back to exact source evidence; clinician-approved expected outputs.

#### C-03 — Clinical criteria are inconsistent across engines and conflict with the approved working instruction

**Classification:** Finding — clinical correctness / safety.  
**Evidence:** The approved working instruction, pages 2-4, requires qualifying BP observations at least six hours apart and within one week, HELLP LDH above 600, and acute kidney injury via absolute creatinine and/or baseline doubling. `backend/services/derivation_engine.py:24-44,122-210` uses four hours, has no one-week upper bound, and permits distinct-date/severe-recheck fallbacks; `:413-431` derives an LDH threshold of 500 from a hard-coded ULN. `backend/services/dv_engine.py:141-166` uses a different date/severe shortcut; `:279-301` does not implement the passed baseline-doubling evidence; `:329-347` uses 600 for LDH. `backend/api/derive.py:172-225` runs both engines while presenting one rule-version surface. Browser decisions also use `src/services/dvEngine.js` (`src/components/AdjudicatorWorkbench.jsx:6`), creating another executable authority.  
**Impact:** The same patient evidence can receive different qualification, severity, HELLP, or renal results depending on path and runtime. This is unacceptable for endpoint adjudication and invalidates validation evidence.  
**Root cause:** No single approved, versioned clinical rule service or requirements-to-test traceability matrix. Duplicate server/client implementations have drifted.  
**Correction:** Stop automated confirmation until the sponsor/medical monitor approves a machine-readable rule specification. Implement one server-side engine, treat results as decision support only, and make the frontend render signed server results. Remove or quarantine duplicate engines. Enforce the exact temporal windows, units, threshold inclusivity, baseline logic, gestational boundary, and not-assessable rules approved for each protocol/version.  
**Addition/acceptance evidence:** Signed clinical specification; requirements trace matrix; boundary tests (including 5:59/6:00 hours, 7-day edge, 33+6/34+0, 599/600/>600 as specified); unit conversion tests; blinded clinician validation; formal rule-version migration and re-derivation policy.

#### C-04 — Legacy exports fabricate clinical content and mix synthetic rows with repository data

**Classification:** Finding — clinical integrity / confidentiality.  
**Evidence:** The unauthenticated PDF route at `backend/api/export.py:54-107` fills real or unknown subjects with hard-coded gestational age, dates, diagnosis, severe features, BP, laboratory, delivery, and “100%” completeness. The unauthenticated CSV at `:110-152` exports subject/site fields and unconditionally appends every `DEMO_MAP` row after database rows. The separate final-study routes at `:404-463` are authenticated and audited, showing a safer implementation exists but does not remove the unsafe paths.  
**Impact:** A report can assert clinical facts never present in source evidence; a dataset can mix synthetic and live records; unauthenticated callers can obtain identifiers and outcomes. These are direct risks to trial endpoints and participant confidentiality.  
**Root cause:** Demonstration fallbacks are mounted in the production application instead of isolated behind compile/deploy boundaries.  
**Correction:** Remove legacy routes from production and fail closed when a record or required evidence is absent. Generate only from locked, versioned canonical records. Mark every field with provenance/missingness and prohibit synthetic rows in non-demo databases and exports.  
**Addition/acceptance evidence:** Export schema/data contract; negative tests for unknown/unfinalized cases; demo/live contamination test; reconciliation of export counts/hashes to locked records; clinical and data-management approval of representative PDF/CSV artifacts.

#### C-05 — Electronic signature identity, MFA, assignment, and record-integrity binding are insufficient

**Classification:** Finding — electronic records/signatures / authorization.  
**Evidence:** The adjudication API looks up a reviewer from a submitted UPN/password instead of binding the signature exclusively to the active session (`backend/api/adjudication.py:240-265`). Assignment is enforced only when a `SubjectAssignment` exists (`:273-336`), while synchronization creates one only after both RealTime A/B assignments exist (`:186-203`). Signature generation covers a selected concatenation rather than a canonical immutable record (`:471-521`) and sets `mfa_verified=True`; the UI pre-populates a demo OTP and claims the record will be cryptographically locked and filed directly to TMF (`src/components/SignatureModal.jsx:5-11,142-143,183-199`). Model constraints do not make signed adjudications or locked decisions immutable at the database layer (`backend/models/canonical.py:431-550`).  
**Impact:** A credential holder may sign outside the intended assignment, the MFA assertion is not genuine step-up authentication, and later changes outside the hashed subset may not invalidate the signature. The user-facing claim overstates the control.  
**Root cause:** Prototype password/OTP flows and application-only lock checks were treated as signature controls.  
**Correction:** Bind signing to the authenticated session, active assignment, purpose, and re-authenticated MFA assertion from the identity provider. Hash a canonical serialized record plus referenced evidence/rule/template versions and artifact digest. Make signed/locked records append-only with database-enforced controls; corrections must create superseding versions. Fail signing if eTMF filing is required and not acknowledged.  
**Addition/acceptance evidence:** Part 11/e-signature applicability assessment; signature threat model; IdP step-up integration tests; canonicalization specification; tamper tests; signer manifestation on artifact; controlled correction/reopen SOP and audit tests.

#### C-06 — Raw direct identifiers are staged on ordinary storage and cryptographic identity controls can fall back to known defaults

**Classification:** Finding — privacy / cryptography / retention.  
**Evidence:** Uploads are copied to a persistent staging directory before processing (`backend/api/realtime.py:143-173`), backed by a Docker volume (`docker-compose.yml:8-10`). Identity crosswalk protection derives from environment secrets that have fallback values rather than refusing import (`backend/services/realtime_pipeline.py:15-20`); the README itself warns that unset/changed keys weaken or orphan pseudonyms/crosswalks (`README.md:226`). No implemented staging cleanup/retention lifecycle was found.  
**Impact:** Raw extracts containing direct identifiers can remain on disk beyond operational need; missing configuration produces predictable/deterministic protection; rotation can destroy linkage. Compromise or backup propagation can expose participant identities.  
**Root cause:** Prototype filesystem ingestion and convenience defaults, without a production key-management or retention design.  
**Correction:** Hard-fail startup and all imports unless independent high-entropy pseudonym and encryption keys are supplied by an approved vault. Stage in encrypted, access-controlled object storage or ephemeral encrypted volumes; securely delete/quarantine by defined lifecycle. Encrypt crosswalk data with key identifiers and supported rotation/re-encryption.  
**Addition/acceptance evidence:** Data-flow/privacy impact assessment; key hierarchy and rotation ceremony; storage encryption/access evidence; retention/legal-hold schedule; deletion verification; backup scope; incident response and key-loss recovery test.

### High findings — 12

#### H-01 — Newer RealTime endpoints still violate least privilege and reviewer anonymity

**Classification:** Finding — authorization/privacy.  
**Evidence:** `authenticated()` intentionally permits any role (`backend/api/realtime.py:99-102`); batch upload/list/control use it (`:143-205`), patient list/detail are broadly exposed (`:319-355,567-573`), and progress returns reviewer UPNs (`:746-764`). The assigned-case route applies assignment checks at `:829-838`, proving object-level scoping is available but not consistently used.  
**Correction:** Separate Monitor import/QC permissions from assigned-reviewer read access; scope every query before serialization; pseudonymize reviewer identities outside QC/committee need; test cross-role and cross-study access.

#### H-02 — Corrected and superseded source results are not represented safely

**Classification:** Finding — data lineage/integrity.  
**Evidence:** Observation deduplication fingerprints include the value (`backend/services/realtime_pipeline.py:188-191`), so a corrected value becomes an additional observation rather than a version replacing the prior result. Reprocessing deletes and rebuilds staged-derived records (`backend/api/realtime.py:193-228`) without a source correction/version model or locking protocol.  
**Correction:** Model source record identity, source version, correction reason, effective time, superseded-by link, and immutable raw lineage. Derivation must select the approved current result deterministically and show corrections to reviewers. Add concurrent reprocess/import tests and reconciliation reports.

#### H-03 — Audit trails are fragmented, mutable by default, and not tamper evident

**Classification:** Finding — audit/compliance.  
**Evidence:** Canonical, authentication, longitudinal, Admin, and Monitor audit models coexist. ORM listeners protect some Admin/Monitor updates (`backend/services/admin_security.py:119-122`, `backend/models/monitor.py:36-39`), but `AuditEvent` is only described as immutable and has no database trigger/append-only storage (`backend/models/canonical.py:620-646`). The longitudinal event hash excludes details and before/after content (`backend/services/realtime_pipeline.py:28-30`). Local browser workflows are not represented.  
**Correction:** Define one audit event envelope and mandatory coverage catalog. Send append-only events to protected storage with chained hashes/signatures and trusted timestamps. Restrict reads, record export/access events, and continuously verify gaps and chain integrity.

#### H-04 — Data queries and recusal are browser simulations, not governed workflows

**Classification:** Finding — workflow integrity.  
**Evidence:** `src/App.jsx:169-194` implements recusal as an alert/navigation and stores a query in browser local storage rather than a backend case record. No controlled owner, SLA, notification, response, closure, reassignment, or audit lifecycle was found.  
**Correction:** Implement server-side query and recusal entities with reason codes, attachments/provenance, status transitions, permissions, assignment impact, notifications, timestamps, immutable history, and overdue escalation. Remove clinical content from local storage.

#### H-05 — Import jobs are not durable, restart safe, or concurrency safe

**Classification:** Finding — reliability/data integrity.  
**Evidence:** Upload routes schedule `process_batch` using FastAPI `BackgroundTasks` (`backend/api/realtime.py:143-173`); the production container runs the web process directly, with no durable queue/worker (`docker-compose.prod.yml`; `Dockerfile`). Progress commits occur during processing, but there is no lease, heartbeat, idempotent checkpoint/resume, or orphan recovery protocol.  
**Correction:** Use a durable queue and dedicated workers with idempotency keys, row/event checkpoints, job leases, heartbeat, bounded retry/dead-letter policy, cancellation state machine, and restart recovery. Lock reprocess/delete against active jobs.

#### H-06 — Database startup, fallback, and migrations are not production safe

**Classification:** Finding — deployment/data integrity.  
**Evidence:** Hard-coded database defaults and silent PostgreSQL-to-SQLite fallback are implemented at `backend/database.py:18-68`. Importing the application calls `create_all`, performs SQLite compatibility mutations, and may seed demo state (`backend/main.py:24-116`). `backend/scripts/init_prod.py:182-278` creates tables then replays raw SQL files without a migration ledger/checksum; both similarly named migration variants can be discovered, and drift checks focus on missing columns rather than complete schema equivalence.  
**Correction:** In production, fail startup on database/configuration errors. Remove schema mutation and seeding from application import. Adopt one transactional migration tool with immutable version ledger/checksums, preflight/backup, locks, forward and rollback/restore procedures, and full schema drift comparison.

#### H-07 — RealTime calibration shows substantial clinically plausible mapping gaps

**Classification:** Finding — mapping completeness.  
**Evidence:** Repository classifier calibration found 532 populated `UNMAPPED` rows in Source 11 and 2,168 in Source 12; governed review identified 274 and 349 distinct clinically plausible label/page pairs respectively. Examples include growth/SGA measurements, newborn disorder assessment dates, NEC variants, hospitalization, physical-exam systems, sample/assessment timestamps, visit type, resource utilization, and adverse-event fields. Some are legitimately out of scope; the absence of disposition is the finding.  
**Correction:** Create a signed mapping disposition register: canonical mapping, prohibited, operational-only, derived-only, not relevant, or query-required. Normalize spelling/unit variants; version by source-system/study/form; require dual clinical/data-management approval and regression fixtures for every mapped variable.

#### H-08 — Ingestion lacks required format coverage and hostile/oversized file controls

**Classification:** Finding — functional/security.  
**Evidence:** The production RealTime route accepts only filenames ending in `.csv` and writes the upload (`backend/api/realtime.py:143-168`); there is no XLSX parser, byte/row/decompression limit, MIME/magic validation, malware scanning, or quarantine service. Legacy import reads uploaded data without equivalent controls (`backend/api/import_api.py:59-88,157-186`).  
**Correction:** Add a quarantined streaming ingest service for approved CSV/XLSX templates, strict content signature and schema validation, bounded size/rows/cells/time, zip-bomb protections, malware scanning, encoding policy, safe formula handling, and reject reports that never echo sensitive content.

#### H-09 — Unhandled exceptions expose internal details to clients and logs

**Classification:** Finding — information disclosure/operations.  
**Evidence:** The global handler logs a full traceback and returns the exception string and traceback in the HTTP response (`backend/main.py:198-202`). Clinical/import exceptions can therefore expose paths, SQL, internal state, or sensitive values.  
**Correction:** Return stable correlation IDs and generic error contracts; log structured, redacted details only to restricted telemetry. Add secret/identifier redaction tests and production debug-off assertions.

#### H-10 — Optional external AI narrative generation lacks a complete governance boundary

**Classification:** Finding — privacy/clinical content governance.  
**Evidence:** Narrative generation invokes an external OpenAI client whenever a key is configured (`backend/api/narrative.py:252-288`). The route is unauthenticated, the repository does not establish an approved data-processing boundary, field allow-list by protocol, residency/retention setting, model/version validation, prompt-injection control, or documented human-verification gate. Output screening is not equivalent to input minimization.  
**Correction:** Disable external AI in production until approved. If retained, use an explicit minimal allow-list of blinded evidence, approved enterprise endpoint/settings, model and prompt versioning, injection-resistant templating, output provenance, mandatory human approval, monitoring, DPIA/vendor assessment, and deterministic fallback.

#### H-11 — The automated suite is not release green and contains state leakage/stale contracts

**Classification:** Finding — verification.  
**Evidence:** Full backend execution produced 347 passes and 14 failures. One was sandbox-specific; three Monitor tests passed alone and therefore reveal suite state leakage. Remaining failures include import-readiness gate ordering versus contract/capacity expectations and Reviewer C scenarios whose fixtures omit a newly mandatory differential diagnosis.  
**Correction:** Make all tests isolated and deterministic; update fixtures only after confirming requirements; test gate precedence explicitly; run PostgreSQL-backed integration tests and prevent merge/deploy unless all safety-critical suites pass. Do not waive order-dependent failures.

#### H-12 — Missing evidence can be presented as negative/zero and automated text overstates diagnosis

**Classification:** Finding — clinical display safety.  
**Evidence:** Absent risk-summary data defaults gravidity/parity and outcome counts to zero and chronic hypertension/diabetes to `False` (`backend/api/realtime.py:551-566`). Several DV missing-data branches use unrelated platelet/AST wording (`backend/services/dv_engine.py:279-332`). Severity text states “confirmed by automated criteria” (`:357-378`), contrary to decision-support-only adjudication.  
**Correction:** Preserve three-state/typed missingness from source to UI/export; never coerce unknown to false/zero. Generate criterion-specific messages from one metadata catalog. Label all derivations as nonbinding support and require reviewer confirmation with source provenance.

### Medium findings — 10

#### M-01 — Admin and Owner production capabilities are materially incomplete

**Classification:** Finding — product completeness.  
**Evidence:** Production routing disables Owner (`src/App.jsx:210-231`); Owner metrics/audit/determinations include hard-coded values (`src/owner/OwnerPortal.jsx:112-218`). The production Admin build exposes only a narrow user/health subset while other screens contain simulations (`src/admin/AdminPortal.jsx:1805 onward`; `README.md:239-250`).  
**Correction:** Define the production role matrix, remove nonfunctional navigation, and implement each approved function against authorized, audited APIs. Do not count disabled/demo screens as delivered acceptance criteria.

#### M-02 — A mounted workflow API is a hard-coded mock

**Classification:** Finding — workflow completeness.  
**Evidence:** `backend/api/workflow.py:43-118` relies on caller-supplied roles and hard-coded release/state responses without database persistence or authenticated transition control.  
**Correction:** Remove it from production or replace it with persisted, role-authorized transitions with state preconditions, idempotency, reason, actor, timestamps, and audit records.

#### M-03 — Frontend failure and navigation states can mislead users or lose work

**Classification:** Finding — usability/safety.  
**Evidence:** Assigned-case loading converts errors to an empty queue (`src/App.jsx:60-66`). No general unsaved-change navigation guard was found for clinical forms. Several actions use alerts/confirmations without durable status.  
**Correction:** Distinguish empty/loading/unauthorized/offline/server-error states; retain recoverable drafts under controlled server storage; warn and block navigation with unsaved changes; make submission idempotent and show authoritative server state.

#### M-04 — Accessibility and responsive behaviour lack validation and key modal semantics

**Classification:** Validation gap with confirmed implementation omissions.  
**Evidence:** Signature modal markup lacks a clear dialog/focus-trap/return-focus implementation and relies on visual labels (`src/components/SignatureModal.jsx:90-199`). E2E covers only desktop Chromium and contains no automated accessibility assertions (`playwright.config.js`; `tests/e2e/test_full_portal_flow.spec.js`).  
**Correction:** Target WCAG 2.2 AA; implement semantic dialogs, focus management, keyboard/Escape behaviour, associated labels, live error summaries, contrast and zoom/reflow support. Test with axe, keyboard-only, screen readers, 200-400% zoom, and supported mobile/tablet widths.

#### M-05 — Performance capacity is unproven and the frontend payload is large

**Classification:** Validation gap / scalability.  
**Evidence:** Production build emitted a 1,246.77 kB JavaScript bundle and Vite chunk-size warning. Several collection routes lack bounded pagination and timeline serializers perform multi-relationship processing (`backend/api/realtime.py:319-355,356-573`). No load, soak, large-file, or concurrency results were found.  
**Correction:** Add route-level code splitting, bounded pagination/filtering, query-count budgets, indexes proven by execution plans, streaming exports, and capacity tests using maximum expected participants, observations, users, and concurrent imports.

#### M-06 — Backup, restore, observability, alerting, and incident controls are absent from deployable evidence

**Classification:** Gap — operations.  
**Evidence:** The repository has no executable backup/restore verification, metrics/SLO dashboards, alert rules, log-retention policy, runbook, disaster-recovery exercise, or incident playbook. `README.md:252-254` explicitly lists these as hardening still required.  
**Correction:** Define RPO/RTO, encrypted backups including identity/crosswalk/artifacts, scheduled restore tests, health/SLO metrics, audit and security alerts, on-call escalation, incident/rollback/runbooks, retention, and evidence ownership.

#### M-07 — Supply-chain validation is incomplete despite a clean npm production audit

**Classification:** Validation gap — security.  
**Evidence:** npm reported zero known production vulnerabilities, but no Python vulnerability scan, SBOM, signed provenance, dependency license policy, container image scan, or secret scan result was available.  
**Correction:** Generate SBOMs for Python/Node/container, pin and hash Python dependencies, scan dependencies/images/secrets/licenses in CI, define remediation SLAs and exceptions, and sign build artifacts/provenance.

#### M-08 — Documentation describes both production capabilities and prototype limitations inconsistently

**Classification:** Finding — documentation/governance.  
**Evidence:** README portal/API descriptions assert controlled authenticated workflows (`README.md:3-27,70-80`), while the same document acknowledges demo session auth and substantial production hardening (`:60-63,239-254`). Architecture verification numbers are stale (`ACRN_APP_COMPLETE_FUNCTION_AND_ARCHITECTURE_GUIDE.md:473-480`) relative to the 361-test run. `backend/main.py:121-132` says all endpoints require authentication, contradicted by C-01.  
**Correction:** Maintain an approved current-state architecture, route policy matrix, data-flow diagram, clinical rule version, known-limitations register, and verified release evidence generated from CI. Remove statements that exceed implemented controls.

#### M-09 — Final artifact and eTMF lifecycle needs fail-closed qualification

**Classification:** Validation gap — records management.  
**Evidence:** `backend/services/case_finalization.py:35-82` builds an artifact and `backend/services/etmf_adapter.py` supports local/fallback-oriented behaviours. UI wording states direct TMF filing even though external connectivity is explicitly simulated (`src/components/SignatureModal.jsx:142-143`; `README.md:239-250`).  
**Correction:** Separate “signed locally,” “transfer pending,” “filed,” “verified,” and “failed” states. Validate template pagination, metadata, checksum, duplicate handling, retry/idempotency, receipt reconciliation, retention, and retrieval against the approved eTMF; never claim filed until a verified receipt exists.

#### M-10 — Time, API contracts, and persistence constraints are inconsistent

**Classification:** Finding — maintainability/integrity.  
**Evidence:** Naive `datetime.utcnow()` is widespread and generated deprecation warnings; Pydantic V1-style configuration/minimum-item syntax also generated warnings. `AuthSession.user_id` and committee assignment references are not declared foreign keys (`backend/models/auth.py:33-60`), and reviewer-A/B distinctness is enforced by application logic rather than a database constraint (`backend/models/canonical.py:555-583`).  
**Correction:** Use timezone-aware UTC end to end; publish/version OpenAPI error and state contracts; remove deprecations; add defensible foreign keys/check constraints/unique partial indexes; test integrity under concurrent writes.

### Low findings — 4

#### L-01 — Generated legacy artifact text contains encoding artefacts

**Classification:** Finding — presentation.  
**Evidence:** Legacy PDF narrative literals show mojibake for punctuation/operators at `backend/api/export.py:86-96`.  
**Correction:** Standardize UTF-8 source/font handling and visually regress every controlled artifact. Removal of the unsafe legacy route remains the primary action.

#### L-02 — The repository has no lint or static typecheck release command

**Classification:** Gap — developer quality.  
**Evidence:** `package.json` defines build/test tasks but no lint/typecheck gate; equivalent whole-repository Python lint/type checking is not part of the demonstrated workflow.  
**Correction:** Add reproducible frontend and backend formatting, lint, type, import-cycle, and dead-code checks with safety-critical warnings treated as failures.

#### L-03 — Health checking is too shallow for orchestration decisions

**Classification:** Finding — operations.  
**Evidence:** `backend/main.py:204-211` returns static health information without checking database reachability, migration state, storage, queue/worker, key configuration, or required adapters.  
**Correction:** Split liveness, readiness, and dependency health; do not expose sensitive detail; ensure readiness fails on wrong database, pending migration, missing keys, or unavailable mandatory services.

#### L-04 — Test and runtime warnings obscure signal

**Classification:** Finding — maintainability.  
**Evidence:** The backend run emitted 2,031 warnings, largely Pydantic and naive-datetime deprecations, plus a pytest cache permission warning.  
**Correction:** Establish a warning baseline of zero for owned code, promote new warnings to CI failures, and configure test caches/temp paths deterministically.

## 5. Clinical-rule and source-specification matrix

The approved source is `Supporting resources/EOPE_Adjudication_Working_Instruction.pdf`, especially pages 2-4. The table records only criteria necessary to explain readiness; it is not a substitute for a signed requirements specification.

| Requirement | Approved instruction | Implemented state | Assessment |
|---|---|---|---|
| Qualifying hypertension | At least 140/90 on two occasions, at least 6 hours apart and within 1 week; controlled pre-existing hypertension is also relevant | One engine uses >=4 hours or distinct dates or severe-plus-recheck without a 1-week bound; another uses different date/severe logic | **Unsafe mismatch** |
| Pre-eclampsia | New hypertension plus proteinuria after 20 weeks, or relevant organ/uteroplacental dysfunction | Multiple engines/case builders; mapped evidence may be dropped | **Cannot validate end to end** |
| Proteinuria | 24-hour, dipstick, or spot ratio per protocol thresholds | Thresholds exist, but canonical variable mismatch can omit inputs | **Rule present; data path unsafe** |
| HELLP | AST >70, LDH >600, platelets <100k | One engine derives >500; another uses >=600 and supports “partial HELLP” logic requiring approval | **Inconsistent** |
| Renal severe feature | Creatinine >=1.1 or doubling baseline and/or oliguria | One engine models baseline doubling; another ignores its baseline argument | **Inconsistent** |
| EOPE/LOPE | EOPE <34+0; LOPE >=34+0; near-boundary escalation to at least 3 members | 34-week calculation exists; no complete evidence of the mandated near-boundary committee policy across paths | **Partial** |
| Missing/ambiguous evidence | Do not guess; query or mark not adjudicable | Some explicit missingness exists, but absent risk history becomes false/zero and legacy exports invent facts | **Unsafe** |
| Clinical authority | Independent blinded human adjudication; rule support does not determine outcome | Automated text says severe pre-eclampsia is “confirmed” | **Incorrect framing** |

Before reimplementation, the sponsor should resolve ambiguities such as inclusive/exclusive LDH wording, protocol-specific spot protein/creatinine units, severe-BP repeat timing, chronic-hypertension handling, partial HELLP, uteroplacental dysfunction definitions, and exact near-boundary escalation range. Each decision must have an owner, approval date, protocol/rule version, effective date, and test vectors.

## 6. Import and mapping calibration

No source-row values or identifiers are reported. Counts below are aggregate classifier outputs from the converted files using the repository classifier.

| Metric | Source 11 | Source 12 |
|---|---:|---:|
| Data rows | 3,407 | 16,733 |
| Populated rows | 1,341 | 5,309 |
| Blank rows | 2,066 | 11,424 |
| Permitted clinical | 399 | 1,576 |
| Collection status | 98 | 373 |
| Restricted operational | 182 | 736 |
| Recorded outcome restricted | 7 | 25 |
| Result interpretation restricted | 89 | 302 |
| Direct identifier | 13 | 49 |
| Prohibited | 21 | 80 |
| Unmapped populated rows | 532 | 2,168 |
| Mapped canonical variables | 114 | 129 |
| Distinct clinically plausible unmapped label/page pairs requiring disposition | 274 | 349 |

Visit distribution demonstrates that V01-V06 and additional forms are present, but it does not prove visit reconstruction correctness. Source 11 populated classifications distribute across V01 285, V02 192, V03 182, V04 173, V05 80, V06 179, and other forms 250. Source 12 distributes across V01 1,402, V02 578, V03 561, V04 400, V05 385, V06 902, and other forms 987, including protocol-deviation and adverse-event material.

Positive evidence:

- Header/preamble discovery and encoding handling are implemented (`backend/services/realtime_pipeline.py:64-107`).
- Exact-file checksum rejection exists.
- Direct identifier, prohibited biomarker, restricted operational/outcome/interpretation, and collection-status categories are separated from permitted clinical mapping (`backend/services/realtime_mapping.py:17-33,172-180`; `backend/services/realtime_pipeline.py:162-185`).
- Import readiness retains a missing visit date as a warning rather than erasing an otherwise identifiable visit (`backend/services/import_readiness.py:83-120`).
- Duplicate scheduled visit candidates are ranked deterministically before warning/reporting (`backend/services/import_readiness.py:21-51,108-120`).
- A participant with no scheduled V01-V06 block is rejected; fewer than four usable visits requires Monitor acknowledgment (`backend/services/import_readiness.py:138-172`; `backend/api/realtime.py:591-616`).

Required validation corpus:

- Both supplied sources as locked, de-identified regression fixtures or synthetic equivalents with identical structures.
- XLSX and CSV variants; preambles; reordered columns; quoted newlines; alternate encodings; blank/repeated headers; formula cells; very large and malicious files.
- Repeated visits, noncontiguous form blocks, missing and conflicting dates, corrected results, unit variations, duplicate/sparse visit instances, and cross-midnight timestamps.
- Expected row disposition totals, participant/visit counts, canonical values, missingness, issue records, and derivations signed off by data management and clinicians.

## 7. Security, privacy, and threat assessment

The dominant threats are broken access control, unsafe direct-object access, clinical-record tampering, identity disclosure, synthetic data contamination, and credential/signature impersonation. Relevant trust boundaries are browser-to-API, source system-to-staging, staging-to-canonical store, identity crosswalk-to-blinded store, API-to-external AI/eTMF, and application-to-database.

Controls that are present include HttpOnly session cookies, server-side hashed session tokens, expiry, login lockout, explicit CORS origins, production demo-account/UI disable flags, role dependencies in Admin/Chairperson/newer export areas, mapping exclusions, and access-event creation on parts of the RealTime path. These reduce risk but are undermined by bypass routes.

Before penetration testing, engineering must complete:

- deny-by-default authorization and object scoping;
- CSRF strategy for every state-changing cookie-authenticated request;
- secure-cookie/HSTS/CSP/frame/referrer/content-type policies at the deployed edge;
- session idle and absolute expiry, rotation, revocation, concurrent-session policy, and account deactivation propagation;
- request/rate/size limits for login, upload, search, export, and signature paths;
- output encoding and injection testing for CSV, PDF, logs, filenames, narrative, and formula cells;
- SSRF/path traversal/archive/multipart and malicious-file tests;
- secrets removal and rotation with a vault-backed production configuration;
- privacy-minimized structured logging and audit read authorization.

Formal testing should cover OWASP ASVS-oriented controls, API authorization matrices, dependency/container/secrets scans, SAST, DAST, authenticated penetration testing, and a privacy review. Production-like security testing must use synthetic data only.

## 8. Data model, API, and audit assessment

The SQLAlchemy model contains many useful foreign keys, uniqueness constraints, relationships, and indexes. The longitudinal schema separates restricted identity crosswalk data from blinded participant data, and the canonical domain models signed records and committee decisions. However, the database does not enforce several decisive invariants: immutable signed/locked records, distinct A/B reviewers, referential integrity for some auth assignments/sessions, audit immutability, and one authoritative current source result.

API contracts are uneven. Newer routes commonly use typed request models and role dependencies; legacy routes accept query/body identity and broad defaults. Error behaviour ranges from structured `HTTPException` payloads to swallowed exceptions and full traceback disclosure. Collection pagination, maximum page size, stable sorting, and optimistic concurrency are not systematic.

Required additions:

- a canonical data dictionary with type, units, null semantics, provenance, sensitivity, source priority, validation, and version;
- database constraints for workflow invariants plus concurrency-safe transactions;
- record version/ETag on clinical edits and assignments;
- append-only audit outbox in the same transaction as every regulated state change;
- reconciliation jobs for source-to-canonical, canonical-to-artifact, and artifact-to-eTMF totals/hashes;
- migration tests against a production-equivalent PostgreSQL snapshot and restore rehearsal.

## 9. Test strategy and release validation plan

The existing test volume is a strong base, especially around derivation, import readiness, assignments, finalization, and Admin/Monitor services. The current failures and duplicated rule engines mean it is not release evidence.

Required test layers:

1. **Clinical unit/characterization tests:** approved boundary and missingness vectors for every rule/version; unit conversions; temporal ordering; no automated diagnosis language.
2. **Mapping golden tests:** raw synthetic CSV/XLSX through staging, mapping, reconstruction, correction/supersession, derivation, UI API, signature, artifact, and export.
3. **Database integration tests:** PostgreSQL only for release; constraints, transactions, locks, migrations, rollback/restore, concurrent assignment/signing/reprocess.
4. **Authorization tests:** every endpoint x role x object scope x account state; unauthenticated and forged body/query identity; reviewer blindness and committee phase transitions.
5. **Browser journeys:** Admin provisioning; Monitor import/QC/assignment; A/B independence; query/response; recusal/reassignment; concordance; Reviewer C; Chairperson lock; signing failure/retry; final export. Run across supported browsers and responsive sizes.
6. **Accessibility:** automated axe plus manual keyboard, screen-reader, reflow, contrast, error recovery, and timeout testing.
7. **Security:** SAST/SCA/SBOM/secrets/container scans, DAST, abuse/file tests, penetration test, audit tamper test.
8. **Performance/resilience:** maximum file, concurrent imports/reviews/exports, restart during each job phase, database failover, storage/eTMF timeout, queue retry/dead letter, load and soak.
9. **Operational qualification:** clean install, upgrade, rollback/restore, key rotation, backup restoration, monitoring/alert firing, incident drill.
10. **UAT/validation:** protocol-specific scripted evidence with independent clinical/data-management/QA sign-off and traceability to requirements and defects.

No release candidate should proceed while any Critical/High defect is open, the full suite is non-green, production migrations have not been rehearsed, or a safety-relevant requirement lacks traceability and an approved test.

## 10. Production architecture additions

The minimum production design should add:

- managed PostgreSQL with encryption, point-in-time recovery, tested restore, least-privilege service accounts, connection pooling, and no fallback database;
- private encrypted object storage for quarantine/staging/artifacts with malware scanning, lifecycle, legal hold, and access logs;
- durable job queue and dedicated import/export workers with leases, idempotency, retry/dead letter, and autoscaling bounds;
- approved IdP federation and step-up MFA for signing, centralized authorization policy, and short-lived server sessions;
- secret manager/HSM-backed keys with rotation/versioning and separate pseudonym/encryption/signing purposes;
- append-only audit/WORM destination and transactional outbox;
- observability for request/job latency, mapping/rejection counts, queue age, rule/version distribution, signature/export/eTMF failures, authorization denials, audit gaps, and storage growth;
- deploy-time migration job, signed immutable images/SBOM, canary or blue/green release, health-gated rollback, and environment promotion with validation evidence;
- network segmentation, TLS termination, WAF/rate limits, egress allow-list for approved external services, and restricted administrative access.

## 11. Documentation and controlled records required

The following are missing or not yet adequate for production:

- approved user requirements and intended-use statement;
- architecture, trust-boundary, deployment, and data-flow diagrams;
- protocol-to-clinical-rule specification and traceability matrix;
- canonical data/mapping dictionary and unmapped-field disposition register;
- role/permission/object-scope matrix and segregation-of-duties policy;
- electronic records/signatures and regulatory applicability assessment;
- validation plan, risk assessment, test protocols/evidence, deviation report, and validation summary;
- installation, configuration, migration, rollback, backup/restore, disaster recovery, monitoring, incident, and business-continuity runbooks;
- privacy impact assessment, retention/legal hold/deletion schedule, vendor/AI/eTMF data-processing approvals;
- account provisioning/deprovisioning, access review, recusal, data-query, correction/reopen, rule change, mapping change, and emergency-access SOPs;
- release notes, known limitations, support model, training materials, and controlled operator/adjudicator manuals.

## 12. Prioritized remediation roadmap

### Phase 0 — Contain immediately (before any live or pilot data)

**Owners:** Product owner, security lead, clinical safety officer, backend lead.  
**Exit criteria:** no live data; unsafe routes unreachable; evidence preserved.

- Explicitly classify the system as prototype/non-production in deployment and user documentation.
- Disable legacy import, mapping, derive, narrative, adjudication, committee, audit, export, and mock workflow routers outside a synthetic demo environment.
- Disable external AI, local eTMF claims, and RealTime upload wherever approved keys/storage are absent.
- Rotate any credentials/keys ever used beyond isolated demo, without recording values in tickets or this report.
- Freeze clinical rules and exports pending sponsor approval.

### Phase 1 — Safety and security foundation

**Owners:** Security/identity, backend, database, privacy, QA.  
**Exit criteria:** C-01, C-05, C-06, H-01, H-03, H-06, H-08, H-09 closed with automated evidence.

- Implement deny-by-default identity/object authorization and route inventory.
- Integrate IdP sessions and step-up MFA; redesign signature and immutable record versioning.
- Implement safe storage, secrets/key lifecycle, retention, audit outbox/WORM, and fail-closed configuration.
- Establish production PostgreSQL migrations, constraints, backup/restore, and no-fallback startup.
- Add safe upload quarantine and platform security controls.

### Phase 2 — Clinical and data correctness

**Owners:** Medical monitor/clinical safety, data management, backend, frontend, biostatistics, QA.  
**Exit criteria:** C-02, C-03, C-04, H-02, H-07, H-10, H-12 closed; signed clinical/mapping specifications and golden results approved.

- Approve one protocol/versioned rule specification and one server-side derivation implementation.
- Repair canonical normalization and measurement correlation; add correction/supersession lineage.
- Complete mapping dispositions using both supplied structures and approved source dictionaries.
- Remove synthetic export behaviour and validate locked-record artifacts.
- Replace unknown-to-zero/false behaviour and constrain or remove external AI.

### Phase 3 — Workflow and operational completion

**Owners:** Product, Monitor/operations representatives, clinical adjudicators, platform/SRE, records management.  
**Exit criteria:** governed query/recusal/reassignment, durable jobs, verified eTMF lifecycle, complete production portals, operational runbooks and monitored SLOs.

- Implement queries, recusal, reassignment, reopen/correction, notifications, SLA/escalation, and deterministic committee transitions.
- Move imports/exports to durable workers and implement recovery/reconciliation.
- Complete only the approved Admin/Owner functions; remove simulations.
- Qualify eTMF transfer and receipts; add monitoring, alerts, incident/DR processes.

### Phase 4 — Validation and release qualification

**Owners:** Independent QA/validation, security testing provider, clinical/data owners, release authority.  
**Exit criteria:** all automated suites green; no open Critical/High issues; Medium risks accepted by named authority; UAT/OQ/PQ/security/accessibility/performance evidence approved; rollback/restore demonstrated.

- Execute the full test strategy in a production-equivalent environment with synthetic data.
- Reconcile requirements, risks, tests, defects, and released binaries/configuration.
- Conduct independent penetration, accessibility, clinical UAT, and operational qualification.
- Approve deployment, support, training, data migration, rollback, and post-release surveillance plans.

## 13. Go-live checklist

Every item is mandatory unless a named accountable authority records a time-bounded, risk-assessed exception. Critical and High findings are not waivable for go-live.

### Clinical/data

- [ ] Clinical specification and rule version signed by sponsor/medical monitor.
- [ ] One authoritative rule engine; duplicate implementations removed or non-executable.
- [ ] Boundary, missingness, unit, temporal, and protocol-version golden tests pass.
- [ ] Source-to-canonical-to-display-to-export traceability demonstrated.
- [ ] Both supplied source structures dispositioned; zero unreviewed clinically plausible mappings.
- [ ] Correction/supersession, duplicate, visit reconstruction, and reconciliation validated.
- [ ] Unknown never coerced to negative/zero; no fabricated clinical facts.

### Security/privacy/signatures

- [ ] All routes authenticated and explicitly authorized; route matrix complete.
- [ ] Horizontal/vertical/object/study/site/assignment tests pass.
- [ ] IdP, deprovisioning, session lifecycle, CSRF, headers, rate limits, and step-up MFA validated.
- [ ] Signature binds authenticated signer, full record, evidence/rule/template versions, time, and artifact digest.
- [ ] Signed/locked/audit records are append-only and tamper tests pass.
- [ ] Approved keys/vault, rotation, encrypted storage, retention/deletion, and privacy assessment complete.
- [ ] Penetration/SAST/DAST/SCA/SBOM/container/secrets scans meet policy.

### Workflow/product

- [ ] Monitor approval, assignment, capacity, contract, and completion gates are deterministic.
- [ ] Reviewer independence and blindness cannot be bypassed.
- [ ] Query, recusal, reassignment, Reviewer C, Chairperson, correction/reopen, and escalation are persisted/audited.
- [ ] No demo/simulated/hard-coded content or routes in production build/runtime/database/export.
- [ ] Loading, empty, error, offline, conflict, retry, and unsaved states validated.
- [ ] WCAG 2.2 AA and supported browser/device matrix approved.

### Operations/release

- [ ] PostgreSQL-only production startup; migration rehearsal and schema drift check pass.
- [ ] Durable workers recover from restart; retry/dead-letter/cancellation tested.
- [ ] Backup restore meets RPO/RTO; DR, rollback, and incident drills pass.
- [ ] Liveness/readiness, logs, metrics, traces, alerts, dashboards, and on-call runbooks approved.
- [ ] eTMF receipt/reconciliation, PDF visual approval, and export count/hash reconciliation pass.
- [ ] Full unit/integration/E2E/security/accessibility/performance/UAT suites are green.
- [ ] Release image/configuration/SBOM are immutable, signed, and traceable to validation evidence.
- [ ] Training, support, SOPs, access review, known limitations, and change control are active.

## 14. Baseline readiness scoring

This table preserves the original assessment score. The current, post-tranche score and category-by-category changes are recorded in the Current remediation checkpoint above.

| Category | Score /5 | Evidence behind score | What is required for next level |
|---|---:|---|---|
| Clinical-rule correctness | 1 | Multiple inconsistent engines; approved criteria mismatches | Approved single engine and golden clinical validation |
| Mapping and data integrity | 1 | Strong classifier concepts, but case-builder defect and unmapped/correction gaps | End-to-end lineage, correction model, complete dispositions |
| Privacy and blinding | 2 | Field classification/crosswalk separation exist; staging/key/access risks remain | Fail-closed keys/storage/retention and scoped access |
| Authentication and authorization | 1 | Some robust role dependencies, but broad unauthenticated surface | Universal deny-by-default route/object policy |
| Monitor/QC workflow | 2 | Real readiness/assignment controls; broad access and nondurable import | Durable, least-privilege, fully reconciled QC workflow |
| Adjudicator workflow | 2 | Functional workbench and determination model | Correct evidence, controlled query/recusal, genuine signing |
| Committee/Chairperson workflow | 2 | Protected newer chair routes; unsafe legacy committee bypass | One persisted, authorized, fully tested resolution path |
| Admin/Owner governance | 1 | User/health functions exist; production Owner and many actions incomplete | Approved production functions backed by audited APIs |
| Audit and electronic signatures | 1 | Event/signature records exist; fragmented, mutable, weakly bound | Append-only unified audit and validated step-up signature |
| Exports and eTMF records | 1 | Protected final exports exist; unsafe legacy artifacts and unqualified filing | Locked-source-only exports and verified eTMF receipts |
| Reliability and performance | 1 | Basic processing works; no durable jobs/capacity evidence | Worker recovery plus load/soak/concurrency qualification |
| Deployment and operations | 2 | Containers/prod overlay/init checks exist | Safe migrations, backups, telemetry, DR, rollback, no fallback DB |
| Automated testing and validation | 2 | 347 backend and 2 frontend tests pass | Fully green isolated suite and full regulated validation evidence |
| Accessibility and usability | 2 | Usable structured UI with some accessibility cues | WCAG AA/manual validation and safe error/draft states |
| Documentation and governance | 2 | Extensive README/architecture material and candid limitations | Controlled, current requirements/SOPs/traceability/runbooks |
| **Total** | **23/75** | **30.7%, rounded to 31%** | **All Critical/High findings closed and independently validated** |

## 15. Final recommendation

Do not expose this version to live participant data, clinical adjudicators performing trial decisions, or regulated production workflows. Preserve it as a prototype and test harness while remediation proceeds. The fastest safe path is not to polish every existing screen: first eliminate bypass routes and synthetic fallbacks, establish one authorized longitudinal workflow, approve one clinical ruleset and canonical data contract, and then validate that single path end to end. Only after safety/security foundations and clinical correctness are proven should Owner/Admin breadth, AI assistance, and additional integrations be promoted into production scope.
