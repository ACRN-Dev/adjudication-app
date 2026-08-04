# RealTime longitudinal patient database

The operational source is a checksummed RealTime long-form CSV imported through the Monitor/QC Portal. The browser streams the file as multipart upload; the backend writes one-megabyte chunks to restricted staging and parses the snapshot row by row. A partially processed batch is never marked QC approved or exposed to adjudicators.

## Privacy boundary

- Application subject IDs are keyed pseudonyms (`ACRN-...`).
- MRN, screening number, and randomisation reference are encrypted in the restricted crosswalk table.
- Adjudicator endpoints never import or serialize the crosswalk model.
- Staff audit text, uploaded-file metadata, direct identifiers, recorded site outcome fields, and prohibited biomarkers are excluded from adjudicator evidence.
- sFlt-1, PlGF, sEng, biomarker/POC results, treatment allocation and randomisation allocation are rejected during row classification. Only safe exclusion fingerprints and counts enter the blinding report.

## Controlled mappings and reconstruction

`RT-MAP-1.0` uses Form Title, Form Version, Page Title, Field Label, Field type and Export Variable Name. Scheduled, unscheduled, early-termination and event forms receive separate visit instances. In the current export, instances are provisionally reconstructed from participant/form block boundaries and source order; confidence and Monitor QC state are retained.

## Clinical derivation

Each visit stores immutable observations and a DV result set. Cumulative derivation processes visits chronologically and only includes evidence available at or before the current visit. Recorded RealTime PE diagnosis is comparison metadata, not a derivation input. The system's onset statement is advisory and the adjudicator retains decision authority.

## Production dependencies

Production deployment still requires PostgreSQL/Alembic execution, a vault-managed `RT_PSEUDONYM_SECRET` and `RT_IDENTITY_ENCRYPTION_KEY`, authenticated Entra role/study claims, a durable worker/queue, encrypted object staging with malware scanning, retention/deletion jobs, approved mapping activation workflow, complete unit resolution, formal validation, and load testing.
