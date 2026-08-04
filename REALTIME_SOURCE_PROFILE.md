# RealTime source profile — Mutala 28072026.csv

Metadata-only streaming profile; no MRNs, randomisation values, clinical values or audit-trail names were emitted.

- File size: 185,887,131 bytes
- Field rows: 1,237,950
- Participants / screening identifiers: 487
- Columns: 15
- Forms: 17
- Pages: 94
- Unique field labels: 1,055
- Nonblank export-variable cells: 6,111 across only 12 unique names

Largest forms are Screening/V01 (363,804 rows), Visit 2 (310,464), Visit 3 (191,760), Visit 4 (149,703), Visit 6/EOS (62,370), Visit 5 (30,248), with separate unscheduled, early-termination, adverse-event and protocol-deviation forms.

Critical classification findings:

- “Maternal Preeclampsia Assessment”: 86,699 rows.
- “PE status”, assessment/date and recorded diagnosis/date fields: restricted comparison metadata. They are never evidence inputs or adjudication answers.
- “Biomarker Analysis”: 12,072 rows, including PlGF/sFlt-1 and biomarker-result fields. These are prohibited and quarantined.
- MRN, screening/randomisation references and audit trails are restricted. The streaming adapter emits only a deterministic blinded subject reference and removes raw identifiers and audit-trail content.

Because only 12 unique export-variable names are populated, canonical mapping must primarily use Form Title + Form Version + Page Title + Field Label + Field type. Mapping approval remains a controlled Admin function.
