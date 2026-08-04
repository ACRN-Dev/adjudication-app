# ACRN Clinical Endpoint Adjudication Platform

## Complete function and architecture guide for a first-time audience

This document explains the application as it currently exists in the repository. It is written as source material for a NotebookLM audio or video overview and assumes the audience has no prior knowledge of clinical endpoint adjudication, ACRN, or the software.

## 1. The application in one sentence

The Africa Clinical Research Network, or ACRN, Adjudication Platform is a role-separated clinical operations system that turns blinded study evidence into a controlled, independently reviewed, signed and auditable endpoint determination while keeping administration, quality control and clinical judgment separate.

## 2. The problem it solves

In a clinical study, a site may record blood pressure, laboratory values, ultrasound findings, medications, delivery information and other source evidence. That evidence does not automatically equal a final clinical endpoint. Independent reviewers must assess the evidence under a defined charter and rules, and disagreements may require a committee decision.

The platform supports that process by:

- importing or demonstrating blinded evidence;
- standardising source fields into canonical clinical fields;
- calculating deterministic DV-01 through DV-30 support variables;
- checking whether required evidence is complete;
- preventing an unjustifiably high certainty classification;
- allowing two independent reviewers to work without seeing one another's in-flight answers;
- routing discordant answers to a committee;
- recording signatures and locked outcomes;
- giving Monitor/QC staff operational oversight without adjudication authority; and
- giving administrators configuration and access controls without granting clinical decision authority.

The most important conceptual boundary is this: **the system may organise and derive facts from evidence, but the adjudicator makes the clinical determination.** A pre-existing “PE status,” “preeclampsia diagnosis,” diagnosis date, final diagnosis or similar value in an imported file is not used to determine whether the participant has pre-eclampsia. That would defeat the purpose and independence of adjudication.

## 3. The three portals

### 3.1 Adjudicator Portal

This is the clinical review workspace. It contains the subject queue, evidence review, automated rule display, narrative, determination form, signature flow, locked record view and committee demonstration.

It is designed for adjudicators and committee reviewers. It does not contain user administration or system configuration.

### 3.2 Monitor/QC Portal

This is the operational control workspace at `/monitor`. It follows cases from import through reconciliation, packet preparation, pre-QC, reviewer assignment, final QC and release.

Monitor users can see operational status, missing-evidence classifications, deadlines and controlled-release metadata. They cannot make or alter the clinical determination. In-flight Reviewer A and Reviewer B decision content is withheld.

### 3.3 Admin Portal

This is the governance and configuration workspace at `/admin`. It manages demonstration users, roles, studies, sites, rules, mappings, forms, workflow versions, integrations, audit records, access reviews and reports.

Administrators do not gain clinical case access simply because they are administrators. The portal repeatedly displays this boundary, and the administrative roles have no adjudication control.

## 4. High-level architecture

```text
Browser
  |
  |-- React + Vite single-page frontend
  |     |-- Demo login and portal selector
  |     |-- Adjudicator workspace
  |     |-- Monitor/QC workspace
  |     |-- Admin workspace
  |     |-- Local demo subjects and CSV demo import
  |     `-- JavaScript DV display engine
  |
  `-- HTTP / JSON
        |
        `-- FastAPI backend
              |-- Import and field mapping APIs
              |-- Reconciliation and derivation APIs
              |-- Narrative and report generation
              |-- Reviewer and committee submissions
              |-- Workflow gates and audit APIs
              |-- Admin and Monitor role checks
              |-- Python authoritative clinical services
              `-- SQLAlchemy data models
                     |
                     `-- Local SQLite demonstration database
                         or a future controlled production database
```

The frontend entry point is `src/main.jsx`, and the top-level application controller is `src/App.jsx`. FastAPI starts in `backend/main.py`. It registers separate API groups for import, mappings, reconciliation, derivation, narrative, adjudication, committee, audit, export, workflow, administration and monitoring.

The repository remains usable when external services are unavailable. The header checks backend health and displays either “API Connected” or “Demo Mode.” Synthetic subjects and browser-side demonstrations let a viewer explore the workflow without EDC, eSource, LIMS, Entra ID, SharePoint or eTMF connections.

## 5. Sign-in and role selection

The landing screen displays the official ACRN logo, email field, password field, portal selector, **Access Portal** button and **Request access** button.

The portal selector offers:

- Adjudicator Portal;
- Admin Portal — Clinical Operations Administrator; and
- Monitor/QC Portal — Monitor Reviewer.

In demonstration mode, the email and password are only checked for presence. The selected portal constructs a synthetic identity and role. A visible notice says this is not Microsoft Entra authentication and must not be treated as production security.

**Access Portal** validates that the two input fields are not empty, creates the selected demo identity and opens the corresponding portal. **Request access** displays the route for contacting the ACRN portal administrator.

Direct `/admin` and `/monitor` navigation also has frontend role guards. The Admin and Monitor APIs independently evaluate development headers for role and study scope. These headers are a development adapter, not a production identity solution. Production requires validated Entra tokens and server-derived claims.

## 6. Adjudicator Portal: global header

The adjudicator header is organised into three zones.

### Brand and portal identity

The left zone displays the ACRN logo, “Adjudication Portal,” and the PROTECT-Africa and LOPE-Nigeria study identity.

### Search and recent work

The centre contains a search scope selector, search field, **Search** button, **Recent Studies** control and **Recent Subjects** control.

Search matches a loaded subject ID or case number and selects the matching record. The scope selector visually offers All, Subject ID and Site; the current demo search logic matches subject ID and case number. Recent Studies opens the two demonstration study entries. Recent Subjects lists loaded cases with case number, gestational age, phenotype and status, and selecting one makes it the active case.

### Connection and identity

The right zone shows API Connected or Demo Mode, the current user's name and role, and **Sign Out**. Sign Out clears the in-memory session and returns to the login screen.

## 7. Adjudicator Portal: navigation

The left navigation can collapse into an icon rail and expand again. The same main workflow is also available through horizontal tabs.

The four clinical steps are:

1. Subject Queue.
2. eSource and Evidence.
3. Approve and Sign using FORM-ADJ-15.
4. Locked eTMF Record.

The fourth step is disabled until the active case is finalized. Additional navigation opens Committee Review, QC Portal and Gates, the SOP Library and the User Guide.

The QC shortcut currently returns the user to the evidence-and-gates step. The SOP Library and User Guide open modal reference material. Collapse and expand controls change navigation density without changing the user's current case or step.

## 8. Step 1: Subject Queue

The queue begins empty. A user can load synthetic subjects or import a supported CSV demonstration.

The queue table shows:

- blinded subject ID;
- case number;
- blinded site;
- gestational age at the event;
- derived phenotype display;
- DV-26 evidence completeness score;
- current status; and
- eSource action.

Clicking a row selects it. **Review eSource** selects that case and advances to the evidence step. A signed case is visibly marked Finalized and Signed.

**Load 5 Gate-Test Demo Subjects** loads five synthetic cases designed to exercise different logic paths: a severe EOPE example, a LOPE example, an incomplete-evidence example, a borderline example and a postpartum presentation. **Load ZWE001-0292** loads the focused presentation case. The application also contains PDF and partial-data demonstration case loaders for supported scenarios.

CSV upload parses a supported demonstration extract, derives a blinded case object and adds it to the queue. Before accepting it, the uploader checks column names for prohibited blinded content and recorded clinical outcomes.

It rejects biomarker and unblinding fields such as sFlt-1, PlGF, sEng, biomarker results, point-of-care results and treatment allocation. It also rejects imported recorded outcome fields such as PE status, preeclampsia diagnosis, diagnosis date and final diagnosis. Those values must never pre-answer the adjudication question.

## 9. Step 2: eSource and Evidence

This step is a structured review rather than a raw database dump.

At the top, the reviewer can:

- **Recuse** from the case;
- **Raise data query**;
- **View source documents**; and
- move forward or backward through the workflow.

The evidence surface presents case metadata, pregnancy dating, blood-pressure course, proteinuria, laboratory results, ultrasound or fetal evidence, delivery information, evidence completeness and automated rule results. The exact visible content depends on the selected synthetic or imported case.

### Source-document viewer

The source viewer has Ultrasound, LIMS, Vitals and Delivery tabs. The tabs demonstrate how a reviewer moves from summarised evidence to its blinded source context. **Close** exits without changing the case.

### Data query

The query dialog represents a controlled request for clarification or missing evidence. It captures a query category and question, then **Submit Query** routes the demonstration query to the Adjudication Coordinator. It does not let the reviewer invent a missing value. Cancel and close leave the case unchanged.

### Recusal

The FORM-ADJ-08 dialog records a conflict or reason for recusal. Confirming removes the reviewer from the active case in the demonstration and selects another case where possible. The alert explains that the case is rerouted to an independent non-conflicted reviewer. Recusal is not a clinical outcome.

### Automated support

The DV section shows which criteria were met, not met or not assessable and explains the supporting values. Missing evidence is reported as missing or not assessable, never silently converted to a negative clinical fact.

DV-26 displays evidence completeness. DV-27 displays whether the “Definite” certainty option is open or restricted. A restricted gate states the maximum allowed certainty and why. DV-30 indicates whether the evidence meets a configured adjudication-trigger limb; it does not decide the final PE status.

### Narrative

The browser generates a blinded case narrative from available evidence. The narrative is editable because it supports, rather than replaces, reviewer judgment. **Regenerate narrative** rebuilds it from the current evidence after a short demonstration delay. The interface identifies the demonstration narrative model and does not claim that generated prose is a signed clinical decision.

## 10. Step 3: Approve and Sign

The determination form lets the reviewer select or confirm:

- primary diagnosis;
- onset classification;
- severity phenotype;
- certainty level; and
- narrative or rationale.

The form code switches between FORM-ADJ-15A and FORM-ADJ-15B according to the EOPE or LOPE context. “Definite” is unavailable when DV-27 has restricted the certainty gate. This is a workflow control: the reviewer may still review the case, but cannot claim complete certainty when the required anchors are incomplete.

**Back to Evidence** returns to step 2. **Approve and Sign** opens the signature modal.

The signature modal requires confirmation of signing intent and demonstrates a one-time-code or step-up verification experience. **Resend OTP** simulates another code being sent and explicitly says production will use Entra step-up authentication. **Confirm and Sign** marks the demo case Finalized and Signed, attaches signature metadata and advances to step 4. Cancel closes the modal without signing.

On the backend, a reviewer submission model accepts the reviewer role, identity, meets-criteria answer, diagnosis, onset, severity, certainty, differential diagnosis, rationale and password-confirmed flag. The service creates a SHA-256 signature hash and timestamp. Production still needs real token validation, genuine MFA evidence and a validated electronic-signature implementation.

## 11. Step 4: Locked eTMF Record

This step becomes available only after finalization. It presents the signed result as a locked record and offers output actions such as **Download PDF** and moving to the next case.

The backend PDF endpoint builds a FORM-ADJ-15A-style report using database data when available or a synthetic fallback for known demonstration subjects. The CSV export endpoint produces a canonical outcome dataset. These exports demonstrate the release format; production release still requires scoped authority, final-QC enforcement, approved storage, checksums and eTMF transfer controls.

## 12. Independent dual review and concordance

The backend supports Reviewer A and Reviewer B submissions. A reviewer can normally see only their own submission while independent review is in progress. The system compares the two submissions after both are present.

Concordance comparison considers diagnosis, onset classification and whether endpoint criteria are met in the adjudication endpoint; the workflow policy service additionally defines comparison across primary diagnosis, onset, severity and certainty. Matching submissions become concordant. Differences become discordant and can proceed to committee review.

The reviewer-isolation policy only reveals the other submission after the case reaches a concordant, discordant, committee, finalized or locked state. This prevents Reviewer B from being influenced by Reviewer A's answer.

## 13. Committee Review

The committee demonstration shows a discordant case, Reviewer A's determination, Reviewer B's determination, the differing fields, quorum information and a chair rationale.

**Adopt Reviewer A** and **Adopt Reviewer B** select the proposed final classification. They do not immediately lock it. The chair must provide a rationale. **Sign and lock final committee classification** records the selected outcome as the committee consensus and changes the demo case to Finalized with Committee Consensus.

The backend committee endpoint accepts the adopted reviewer, final diagnosis, onset, severity, certainty, chair identity, rationale, quorum status and member count. It creates a timestamped SHA-256 signature hash, marks the decision locked and finalizes the participant. The workflow policy defines a default quorum of three and limits final locking authority to Chair, Co-Chair or a designated system authority.

## 14. DV-01 through DV-30 clinical-support architecture

The application contains a comprehensive JavaScript derivation module and a Python derivation service. The fuller JavaScript module documents and computes the following concepts:

| DV | Function |
|---|---|
| DV-01 | Maximum systolic and diastolic blood pressure within each visit window. |
| DV-02 | Severe-range hypertension detection. |
| DV-03 | Confirmed hypertension using qualifying repeated or severe-range readings. |
| DV-04 | Gestational age at a target date from an ultrasound dating anchor. |
| DV-05 | EOPE, LOPE, postpartum or unclassifiable onset subtype. |
| DV-06 | Time-ordered evidence table and proposed earliest onset. |
| DV-07 | Significant proteinuria from UPCR, dipstick or 24-hour protein. |
| DV-08 | Platelet-count tiers and thrombocytopenia. |
| DV-09 | Creatinine-unit harmonisation. |
| DV-10 | Renal impairment using the configured creatinine threshold. |
| DV-11 | Liver dysfunction with ACOG and ISSHP-aligned outputs. |
| DV-12 | LDH threshold evaluation. |
| DV-13 | Complete or partial HELLP composite with same-draw considerations. |
| DV-14 | Standard, severe-feature or critical severity grading. |
| DV-15 | Uteroplacental dysfunction composite. |
| DV-16 | Serial maternal weight-gain assessment. |
| DV-17 | Estimated fetal-weight centile validation. |
| DV-18 | Antihypertensive medication exposure. |
| DV-19 | Aspirin or calcium prophylaxis exposure. |
| DV-20 | Delivery-date resolution and source disagreement detection. |
| DV-21 | Gestational age at delivery and discrepancy checking. |
| DV-22 | Gravidity and parity consistency. |
| DV-23 | Controlled comorbidity coding. |
| DV-24 | Maternal composite endpoint components. |
| DV-25 | Fetal and neonatal composite endpoint components. |
| DV-26 | Evidence-completeness score across required evidence classes. |
| DV-27 | Certainty gate for permitting a Definite determination. |
| DV-28 | One-, two- and four-week endpoint-window calculation. |
| DV-29 | Inter-rater agreement and Cohen's kappa. |
| DV-30 | Evaluation of the configured trigger limbs for adjudication. |

The calculations are deterministic: the same accepted inputs and rule version produce the same output. Missing data is preserved as missing. Rule results include explanatory details and inputs so a reviewer can understand why a flag appeared.

Not every low-level DV helper is shown as its own visual card in every demo case. The workbench uses a compact browser DV engine for the most relevant live gate display, while the fuller derivation module and backend support the broader controlled set. Production should use the Python service as the authoritative execution path and preserve the exact rule version with every case.

## 15. RealTime long-form CSV safety layer

The repository includes a RealTime source file profile and a streaming classifier for the approximately 185 MB long-form export. The inspected source contains about 1.24 million rows, 487 participants, 17 forms, 94 pages and more than one thousand distinct field labels.

The streaming design processes bounded chunks instead of loading the entire file into memory. It creates deterministic blinded subject references and removes direct identity columns such as MRN, screening number and randomisation number from output intended for adjudication.

Each row is classified as one of:

- permitted clinical evidence;
- prohibited blinded content;
- restricted recorded outcome; or
- restricted operational metadata.

Biomarker and allocation content is quarantined. Electronic-signature and audit metadata is operational rather than clinical evidence. Recorded PE status and diagnosis fields are restricted even when they exist in the source. Only permitted evidence can be returned by the adjudicator-evidence function.

This layer is currently a safe streaming and classification foundation. Full database staging, asynchronous background jobs, visit reconstruction and a patient-timeline UI for the entire RealTime file remain future integration work.

## 16. Monitor/QC Portal in detail

The Monitor dashboard displays eighteen operational counts, including imports, failures, reconciliation, packet preparation, pre-QC, missing evidence, queries, assignment, adjudication status, recusals, discordance, committee work, final QC, release and failed transfers.

It also shows operational performance examples such as import-to-QC time, adjudicator turnaround, query response time, agreement rate, Cohen's kappa and DV-27-capped cases. Priority notifications highlight blinding quarantine, overdue assignment and failed transfer.

Its navigation groups are:

- Overview: Dashboard.
- Case Intake: Import Batches, Case Queue and Reconciliation.
- Pre-Adjudication: Packet Preparation, Pre-QC, Missing Evidence, Queries and Assignments.
- Adjudication Oversight: Review Status, Recusals and Reassignments, Discordance and Committee Status.
- Finalisation: Final QC, Ready for Release and Released Cases.
- Tools: Reports, Audit History and SOP/User Guide.

Every workspace provides **Controlled action**, **Export demo log**, **Run validation** and row-level **Open** controls. A controlled action asks for confirmation and a reason and reports that the clinical determination was unchanged. Export produces a demonstration log for the current study scope. Validation performs a synthetic check without changing a clinical answer. Open represents drilling into an operational record.

The pre-QC example checks identity/study, blinding, reconciliation and DV completion. Missing Evidence distinguishes a missing item from a negative finding and says whether it blocks release or caps DV-27. Adjudication Status shows timestamps and completion state but not the reviewers' clinical answers. Final QC verifies reviewer completion, discordance resolution, certainty restrictions and traceability.

## 17. Admin Portal in detail

The Admin dashboard reports active studies, configured sites, active users, pending approvals, expiring access, incomplete training, open access reviews and integration warnings. Each metric is a button that opens the relevant register. The action queue routes to access approval, expiry, training or integration work. Environment health displays environment, API, database/schema and the explicit denial of clinical case access.

### Users

The Users page supports search, status filtering, clearing filters, invitation, profile viewing, access review, suspension and CSV export. High-impact actions require confirmation and a reason in the demo. Users are never hard-deleted, and self-approval is prohibited.

### Roles and permissions

The role register explains Technical Administrator, Clinical Operations Administrator, QA/Auditor, Governance Reviewer and Access Reviewer. The permission matrix explicitly denies blinded case content and clinical decisions. High-risk combinations are warned or blocked, including technical admin plus adjudicator, monitor plus reviewer, reviewer plus release approval and self-access approval.

### Studies and sites

Studies are versioned configurations with code, protocol, countries, status, active rule version and mapping version. Sites have approved blinded display names and import identifiers. Active or historically used versions are not edited in place; a successor draft is created.

### DV rules

The register contains DV-01 through DV-30, versions, effective dates, approvals and test status. **New controlled draft** creates the concept of a successor version. **Compare versions** opens the version-comparison demonstration. Activation requires passing tests plus clinical and QA approval. The browser cannot accept arbitrary executable Python.

### Canonical mappings

Mappings describe source system, source field, canonical field, type, unit, requirement, study, version, status and blinding classification. **Test sample CSV** performs a synthetic mapping validation. The permanent prohibited-field registry blocks biomarkers, point-of-care results, treatment allocation, unblinding fields and recorded PE outcomes from adjudicator-facing data.

### Forms and templates

The controlled register represents FORM-ADJ-01, FORM-ADJ-05, FORM-ADJ-08, FORM-ADJ-09, FORM-ADJ-11, FORM-ADJ-15A, FORM-ADJ-15B, reviewer forms, committee forms, final-QC and release forms. A version already used by a case is never overwritten.

### Workflow configuration

The page displays the configured flow from import through mapping, reconciliation, packet preparation, pre-QC, query handling, release to reviewers, dual review, concordance or discordance, committee, final QC, release and archive. Validation prevents a direct import-to-adjudication shortcut, release before final QC, modification after lock and uncontrolled reopening. Committee quorum and chair-signature expectations are shown.

### Integrations

The register represents EDC, eSource, LIMS, Entra ID, SharePoint, eTMF, notifications and export destinations. It shows connection status and credential status without showing any secret. **Test connection** returns a synthetic success or warning. Production secrets must live in an approved vault.

### Audit Trail

The audit viewer supports search, status filtering, clear filters and controlled CSV export. Events include identity, role, action, entity, reason and outcome. There are intentionally no edit or delete controls. Administrative events use append-only records and hash chaining/model guards in the demo backend.

### Access Reviews

The page demonstrates a periodic campaign, completion progress and automatic flags for expiring access, incomplete training or conflict declarations, inactive users and closed-study access. **Generate campaign** requests a reason for creating a controlled campaign.

### Reports and generic registers

Report tiles generate scoped demonstration CSVs for access, permissions, study configuration, rules, mappings, forms, training, access review, configuration changes, integrations, imports and audit summaries. Additional routes cover training/COI, endpoints/windows, units/terminology, clinical dictionaries, import contracts, SOP references and environment health.

## 18. Backend API groups

The backend exposes interactive documentation at `/api/docs` and `/api/redoc` when running locally.

The principal API groups are:

- `/api/import`: EDC import, eSource import and import-batch listing;
- `/api/mappings`: field-mapping retrieval and creation;
- `/api/reconcile`: source-value reconciliation;
- `/api/derive` and inline derivation: deterministic clinical-support calculations;
- `/api/narrative`: narrative generation, retrieval and edit logging;
- `/api/adjudication`: reviewer submission and visibility-controlled status;
- `/api/committee`: final committee locking;
- `/api/audit`: audit retrieval;
- `/api/export`: PDF and canonical CSV output;
- `/api/workflow`: QA release, state retrieval, controlled transition, reviewer view and concordance;
- `/api/admin`: role-protected administration; and
- `/api/monitor`: role- and scope-protected operational monitoring.

EDC import validates required columns, blocks blinded columns, creates participants and canonical fields, and records an import batch. eSource import never overwrites EDC values. It fills gaps where appropriate and flags discrepancies for reconciliation.

## 19. Data model concepts

The canonical clinical model contains participants, import batches, canonical fields, mapping rules, derivation results, narratives, adjudication records, committee decisions and audit events.

Administrative additions represent users, roles, permissions, study access, studies, sites, controlled versions, integrations, access reviews and immutable administrative audit events. Monitor additions represent operational objects and actions separated from clinical decisions.

Additive SQL migration markers are provided for the Admin and Monitor portals. The application does not use a destructive database reset. Demo reset removes and regenerates only records explicitly marked as demonstration administration data.

## 20. Security and governance controls

The current design demonstrates these controls:

- portal and role separation;
- study-scope checks on Admin and Monitor APIs;
- no administrator adjudication authority;
- no automatic technical-admin access to case content;
- prohibited biomarker and allocation fields;
- restriction of imported PE status and diagnosis;
- missing evidence preserved as missing;
- dual-reviewer isolation;
- duplicate submission and workflow-state checks;
- quorum and authority gates;
- no in-place editing of active controlled versions;
- no hard deletion of users;
- self-approval prevention;
- reason capture for privileged actions;
- immutable or append-only audit design;
- certainty restriction when evidence is incomplete; and
- final-QC-before-release policy.

These are strong prototype and architecture controls, but the demo must not be described as production-certified. Some clinical demonstration endpoints do not yet apply a complete production authentication dependency. Production requires Entra token validation, server-side claims, step-up authentication, secret management, approved migrations, regulated validation, retention policies, connected systems, monitoring and formal 21 CFR Part 11 assessment.

## 21. Accessibility and visual design

The interface follows ACRN's navy, orange, teal and blue identity with white and neutral-grey working surfaces. The layout intentionally resembles a dense clinical operations system rather than a decorative analytics dashboard.

Tables use headers and captions, controls have visible labels or accessible names, forms use labels, navigation is keyboard-operable, focus states are visible, status includes words rather than colour alone, and high-impact actions request confirmation. Modal dialogs can be closed without committing an action. Further formal accessibility validation is still appropriate before production release.

## 22. What is fully functional in the current demo

- Role-specific demo entry into all three portals.
- Direct frontend access-denied handling for mismatched roles.
- Subject loading, selection, search and navigation.
- Synthetic and supported CSV case creation with safety checks.
- Deterministic DV support calculations and completeness/certainty gates.
- Evidence, narrative, source-document, query and recusal demonstrations.
- Determination entry and local signing/locking flow.
- Committee comparison, adoption and locking demonstration.
- PDF and CSV backend exports.
- Admin navigation, filters, registers, exports and governed action simulations.
- Monitor queues, operational controls and safe status displays.
- Backend models and endpoints for import, derivation, reviewer submission, committee, workflow, admin and monitor operations.
- RealTime streaming classification foundation.
- Automated regression and security tests.

## 23. What is simulated in demo mode

- Email/password authentication.
- OTP resend and step-up authentication.
- Most Admin and Monitor button mutations shown through prompts, confirmations and alerts.
- External connection tests.
- Notification delivery.
- eTMF transfer.
- Live EDC, eSource, LIMS, SharePoint and Entra connections.
- Some reports and operational records, which use synthetic values.

Synthetic data is visibly labelled and should never be mixed with production data.

## 24. Production dependencies and honest limitations

Before live regulated use, ACRN would need to complete:

- Microsoft Entra ID integration and validated authorization claims;
- production-grade session and token handling;
- genuine MFA/step-up electronic signature;
- complete API authorization coverage for every clinical endpoint;
- controlled PostgreSQL/Alembic deployment;
- secure object storage, malware scanning and quarantine;
- approved EDC, eSource, LIMS, SharePoint, eTMF and notification adapters;
- background processing and restart-safe ingestion for very large extracts;
- production visit reconstruction for the RealTime long-form file;
- approved secret vault and key rotation;
- backup, recovery, retention and legal-hold procedures;
- telemetry, alerting and incident management;
- formal user acceptance, validation and accessibility testing; and
- quality-system approval and applicable regulatory assessment.

## 25. Suggested video story

Start with the clinical problem: evidence is scattered and a recorded diagnosis cannot be trusted as the independent adjudication result. Introduce the three portals and explain separation of duties. Sign in as an adjudicator, load the five demo subjects, compare complete and incomplete evidence, open source documents, show DV-26 and DV-27, generate a narrative and sign a case. Then show how disagreement moves to committee review.

Next, sign in to Monitor/QC and follow the operational journey from import through final release without revealing reviewer answers. Then sign in to Admin and show how users, studies, rule versions, mappings, forms, integrations, audits and access reviews are governed without exposing clinical content.

Finish with the architecture: React in the browser, FastAPI services, deterministic Python rules, SQLAlchemy records and future external integrations. End on the central message: **the platform supports evidence quality, consistency and governance, but preserves independent human clinical adjudication.**

## 26. Verification status at the time of this guide

The latest verification completed successfully:

- 146 backend tests passed;
- the Vite production frontend build passed;
- existing DV and adjudication regression tests passed; and
- new RealTime import-boundary tests passed.

The build reports non-blocking bundle-size and dependency deprecation warnings. These do not prevent the current demonstration from running but should be addressed during production hardening.

