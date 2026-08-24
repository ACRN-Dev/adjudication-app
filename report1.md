# ACRN Adjudication Platform — Application Function Summary

> **Report:** report1.md · **Date:** 2026-08-24 · **Scope:** Functional summary of the ACRN PROTECT-Africa / LOPE-Nigeria Independent Endpoint Adjudication Platform
>
> **Standards referenced by the system:** ICH E6(R2) GCP · 21 CFR Part 11 · EU Annex 11 · GAMP 5 · SOP-ADJ-002 (biomarker blinding)

---

## 1. Purpose

A clinical endpoint adjudication platform for the PROTECT-Africa (EOPE, A202501 v1.2) and LOPE-Nigeria (ACRN-202503 v1.1) studies. It lets an independent Outcome Adjudication Committee (OAC) receive blinded case packets, derive preeclampsia/end-organ criteria from source data, submit independent reviewer determinations, resolve discordance through committee consensus, and file signed, Part 11-style records to an eTMF — while keeping biomarker outputs (sFlt-1/PlGF, sEng, POC) withheld per SOP-ADJ-002.

## 2. Technical Architecture

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI (`backend/main.py`), SQLAlchemy ORM, PostgreSQL in production with automatic SQLite fallback |
| Frontend | React 18 + Vite SPA (`src/`), served as static assets by FastAPI in production |
| Auth | Cookie-based server sessions (bcrypt-12 passwords, SHA-256-hashed session tokens), Microsoft Entra ID SSO (MSAL), demo-account mode gated by env flag |
| Deployment | Docker multi-stage build, docker-compose (dev/localdb/prod), Procfile target, `scripts/init-prod.sh` bootstrap |
| Data ingestion | CSV import pipelines (EDC/eSource canonical + RealTime longitudinal staging) |

## 3. Portals (User-Facing Functions)

| Portal | Route | Primary users | Core functions |
|---|---|---|---|
| **Adjudicator Workbench** | `/adjudication` | Reviewers A/B/C | Case queue, blinded case-packet viewer (source docs, labs, vitals timeline), in-browser derivation/DV display, independent diagnosis submission with e-signature modal (password re-auth + simulated MFA OTP), recusal workflow, data-query raising |
| **Committee Dashboard** | `/committee` | Full committee | Discordant-case review (all reviewers' diagnoses + rationales post-disclosure), Reviewer-C tie-breaker voting, final decision locking (chair identity, quorum attestation, signature hash), meeting minutes view |
| **Chairperson Portal** | `/chairperson` | Committee chair | Completed-adjudication listing, agenda-pack generation, meeting scheduling/sign-off (case closure), meeting report with attendee signatures, eTMF filing hook |
| **Admin Portal** | `/admin` | Study admins | User provisioning & RBAC (roles, portal sub-roles, study scoping, delegation validation), account status/unlock/password reset, committee chair assignments, study/site registries, mapping & workflow definition versions with approval gates, access reviews, admin audit trail, demo-data reset |
| **Monitor / QC Portal** | `/monitor` | Data monitors | RealTime batch upload (checksum-deduplicated), blinding scans, QC approval gates, reviewer assignment (A≠B enforcement), longitudinal patient timeline browsing, issue tracking, record release actions |

## 4. Backend Function Groups (API Routers)

### 4.1 Data Ingestion & Canonicalisation
- **Import API** (`/api/import`) — EDC and eSource CSV uploads → `Participant` + `CanonicalField` rows (edc_value vs esource_value pairs); blinding-column guard rejects biomarker fields at ingest; batches tracked with PARTIAL/FAILED statuses.
- **RealTime Longitudinal Pipeline** (`/api/realtime`, `services/realtime_pipeline.py`) — streaming chunked CSV import of RealTime-CTMS exports; row-level classification (permitted evidence / restricted-recorded / prohibited-blinded) via denylist policy; HMAC-SHA256 pseudonymisation of MRN+screening number; Fernet-encrypted restricted identity crosswalk; checksum deduplication; resume cursors; row fingerprints; staged files under `.rt-staging/`.
- **Mapping** (`/api/mappings`) — field-mapping rule definitions (incl. transformation expressions) driving canonical-field population.

### 4.2 Reconciliation & Derivation
- **Reconciliation** (`/api/reconcile/{subject_id}`) — compares EDC vs eSource per field via `resolve_value`: EDC-wins hierarchy, discrepancy categorisation (value/coding/date), clinically-meaningful flagging within numeric tolerance; writes canonical values back.
- **Derivation Engine** (`/api/derive`, `services/derivation_engine.py`) — ISSHP-2021-aligned derivations: HTN-01/02 (BP criteria, distinct-date confirmation), PROT-01 (proteinuria quantification), RENAL-01 (creatinine harmonisation ×ULN/baseline), HEP-01 (transaminases ×ULN), PLT-01, G-13 gestational-age logic, onset classification EOPE/LOPE.
- **DV Engine** (`/api/adjudication`, `services/dv_engine.py`) — DV-03…DV-30 determination rules producing three-state outcomes (met / not assessable / not met), certainty gating (DV-26 completeness → DV-27 Definite/Probable/Possible ladder), case trigger scoring.
- **Longitudinal Derivation** (`services/longitudinal_derivation.py`) — visit-by-visit cumulative bundles over RealTime observations: earliest hypertension confirmation, organ-dysfunction detection, recorded-vs-derived discrepancy capture.
- **Inline Derivation** (`/api/derive/inline`) — stateless compute endpoint (currently shadowed by router ordering).

### 4.3 Adjudication Workflow
- **Adjudication** (`/api/adjudication`) — case retrieval with per-reviewer filtering, stickiness enforcement against `SubjectAssignment`, password-re-authenticated submission of reviewer diagnoses (certainty, rationale, signature hash), server-side concordance computation, Reviewer-C auto-selection for discordant cases, immutability after signing.
- **Workflow Gates** (`/api/workflow`, `services/workflow_policy.py`) — state machine helpers: PENDING → QA_REVIEW → QA_RELEASED → A/B submissions → CONCORDANT/DISCORDANT → COMMITTEE_PENDING → FINALIZED → LOCKED; QA release gate, quorum arithmetic, transfer authority, signing gate, concordance evaluation.
- **Committee** (`/api/committee`) — discordant-case listing, Reviewer-C determination recording (independence check C∉{A,B}), final decision lock (chair UPN, quorum, locked diagnosis).
- **Chairperson** (`/api/chairperson`) — agenda packs, meetings lifecycle, sign-off closing case sets, minutes/report generation.
- **Assignment** (`/api/assignment`) — monitor-driven workload targets and progress stats across active assignments.

### 4.4 Narrative & Reporting
- **Narrative** (`/api/narrative`) — AI-assisted blinded case-narrative drafting (optional OpenAI integration over non-blinded fields with prohibited-term scan), human editor attribution and edit persistence, FORM-ADJ-15A/B template structure.
- **PDF Generator** (`services/pdf_generator.py`) — adjudication certificates/outcome forms with ReportLab, attestation blocks, signature hashing, eTMF-ready output.
- **Export** (`/api/export`) — outcome PDF per case, bulk CSV of decisions, study-analysis dataset, ADMIN-only unblinded-analysis export (env-flag gated, audited).

### 4.5 Governance & Oversight
- **Audit Trail** (`/api/audit`, multiple `AuditEvent` tables) — event records with actor, reason, previous/new values, request metadata, record hashes across adjudication, auth, admin, monitor, and longitudinal domains.
- **Auth** (`/api/auth`) — login/logout with lockout (5 attempts / 15 min), session issue/revoke, Entra ID SSO round-trip with state cookie, user management endpoints, role/portal-role/study-scope changes (all reason-captured), auth audit reader, demo seeding.
- **Monitor security** (`services/monitor_security.py`) — blinding content scans, QC gates, release gates, reviewer assignment gate (A≠B).
- **eTMF Adapter** (`services/etmf_adapter.py`) — local-filesystem adapter writing meeting reports with SHA-256 sidecars (SharePoint adapter stubbed).

## 5. Frontend Service Layer

| Module | Function |
|---|---|
| `src/services/api.js` | Fetch wrapper with credentials, import submission (demo-attributed), health probe |
| `src/services/authApi.js` | Login/logout/me/auth-config calls |
| `src/services/realtimeApi.js` | Batch upload/listing, patient timelines, approve/assign actions |
| `src/services/derivation.js` (~52KB) | JS mirror of backend derivation engine for instant workbench previews |
| `src/services/dvEngine.js` | JS DV-rule engine powering UI gate displays (GATE OPEN/RESTRICTED) |
| `src/services/demoNarrative.js` | Offline narrative generation fallback when AI is unconfigured |
| `src/components/CsvUploader.jsx` | In-browser CSV parse + validation (blinding guard, required columns, single-participant limit) + client-side derivation preview |

## 6. Data Model Highlights

- **Canonical domain** (`models/canonical.py`): Participant, CanonicalField (EDC/eSource/canonical triplets + discrepant flags), ImportBatch, AdjudicationRecord (per-reviewer), CommitteeDecision (unique per participant, lockable), SubjectAssignment, CommitteeMeeting, AuditEvent, DerivationResult (with captured inputs/source fields).
- **Longitudinal domain** (`models/longitudinal.py`): RtImportBatch (unique checksum), LongitudinalParticipant (blinded_subject_id), VisitInstance, CanonicalObservation (source-page provenance), RestrictedIdentityCrosswalk (Fernet-encrypted MRN/screening/randomisation ref), ReviewerAssignment (unique participant+role), VisitDerivation, ImportIssue, audit events.
- **Auth/admin/monitor domains**: PortalUser (role, portal_role, study_scope, lockout state), AuthSession (hashed tokens), CommitteeAssignment, permission-scoped admin models, monitor QC records.

## 7. Configuration & Operations

- Env templates: `.env.dev.example`, `.env.prod.example` (DB SSL required, SSO credentials, session/lockout tuning, realtime pseudonym secrets, demo accounts pinned off in prod).
- Bootstrap: `scripts/init-prod.sh` validates env, runs `backend/scripts/init_prod.py` (create_all + SQL migrations replay).
- Health: `/health` liveness endpoint reporting service version and blinding posture.
- Tests: 21 pytest modules incl. full-lifecycle e2e, derivation boundary suites, SSO/user-provisioning/realtime-security tests; Playwright portal flow spec.

## 8. Known Gaps (from concurrent audit — see audit findings, 2026-08-24)

This functional summary reflects intended behaviour. The parallel integrity/security audit identified material gaps between intent and implementation — notably ~35% of routes lacking authentication, client-asserted identities/quorums on committee actions, divergent frontend/backend derivation thresholds, unaudited regulated mutations, PHI-bearing CSVs tracked in git, and published fallback crypto keys. Remediation priorities are listed in the audit report delivered 2026-08-24.

---

*End of report1.md*
