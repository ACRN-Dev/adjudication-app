# ACRN Admin Portal operating guide

The Admin Portal is an additive, non-clinical surface at `/admin`. Existing adjudicator, CSV demonstration, derivation, narrative, source-document, query, recusal, committee and signing workflows remain in the original application surface.

## Demonstration access

On the local sign-in screen, select **Admin Portal — Clinical Operations Administrator**. The identity and all administration records are explicitly labelled demonstration data. This is not Microsoft Entra authentication and must not be used as production security.

The FastAPI demo identity adapter uses `X-Demo-User`, `X-Demo-Role`, and `X-Study-Scope` headers. It exists only to make standalone development possible. Every `/api/admin/*` endpoint validates the role and relevant study scope independently; the React route guard is supplementary UX only.

Supported profiles are Technical Administrator, Clinical Operations Administrator, QA/Auditor, Governance Reviewer and Access Reviewer. Administrative identities are denied clinical case content and have no adjudication permissions.

## Main routes

The portal provides dashboard, users, roles/permissions, access reviews, training/COI, studies, sites, endpoints/windows, workflows, mappings, terminology/dictionaries/import contracts, DV rules, forms/templates, SOP references, integrations, immutable audit, reports and environment/health routes.

## Controlled records

Studies, rules, mappings, forms and workflows use version records. Active or historically used versions must not be updated in place; create a successor draft with a reason, validate it, obtain the required approvals, and activate it through a controlled change.

Rule activation requires passing tests and both clinical and QA approval. The Python engine remains authoritative and the browser never accepts executable rule code. Workflow validation prohibits import-to-adjudication shortcuts and release without final-QC readiness.

The permanent prohibited-field registry rejects sFlt-1, PlGF, sEng, biomarker/POC results, treatment allocation and configured unblinding fields from adjudicator-facing mappings.

All privileged operations require a reason and create an append-only hashed audit event. Audit records have model-level update/delete guards. Users are suspended or deactivated, never hard-deleted. Self-approval and delegation above the acting administrator's authority are rejected.

## Demo reset

`POST /api/admin/demo/reset` resets only records carrying `is_demo=true`. It does not truncate tables and does not affect production-marked records or any clinical tables.

## Production dependencies

Before production use, replace the demo identity adapter with validated Microsoft Entra ID tokens and server-derived role/study claims; implement step-up authentication for sensitive approvals; run the additive schema through controlled Alembic/PostgreSQL migrations; connect EDC, eSource, LIMS, SharePoint, eTMF, notification and export adapters; move secrets to an approved vault; add organisation-specific retention/export policies; and complete formal validation, accessibility testing and 21 CFR Part 11 assessment.

## Verification

Run `python -m pytest -q` from `backend` for the combined clinical and admin-security suite, and `npm run build` from the project root. The SQL marker in `backend/migrations/versions/20260803_01_admin_portal.sql` is additive and intentionally has no destructive down migration.
