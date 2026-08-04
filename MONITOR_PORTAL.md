# ACRN Monitor/QC Portal

The Monitor/QC Portal is available at `/monitor` and is separate from the Admin and Adjudicator portals. Select **Monitor/QC Portal — Monitor Reviewer** on the demonstration sign-in screen.

It supports import-batch oversight, case queues, EDC/eSource reconciliation, packet preparation, missing evidence, FORM-ADJ-05 query coordination, FORM-ADJ-01 pre-QC, assignment eligibility, status-only adjudication oversight, recusals, discordance routing, committee status, final QC, controlled release, reports and audit history.

All displayed records are synthetic and labelled demonstration data. Monitor users cannot submit or change clinical determinations. In-flight reviewer decision content is withheld, missing evidence is never converted into a negative finding, and technical administrators do not inherit Monitor access.

Backend access uses the development-only `X-Demo-User`, `X-Demo-Role` and `X-Study-Scope` adapter. Supported roles are `ADJUDICATION_COORDINATOR`, `MONITOR_QC_REVIEWER`, `QA_REVIEWER` and `RELEASE_OPERATOR`. Production must replace this with validated Entra ID tokens and server-derived claims.

Safety gates include prohibited-field quarantine, duplicate/empty/header validation, study scoping, mandatory pre-QC completion, distinct eligible reviewers, reviewer isolation, committee quorum, final-QC-before-release and immutable released packages/audit events.

Production dependencies include approved file quarantine storage, malware/content scanning, connected EDC/eSource/LIMS adapters, document storage, notifications, Entra step-up authentication, formal assignment/COI services, eTMF transfer, checksum signing, Alembic/PostgreSQL deployment and regulated validation.
