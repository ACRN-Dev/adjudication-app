# Software and clinical data risk register

Scales: severity and probability 1–5; initial risk is their product. Residual ratings are provisional until the cited validation evidence is approved.

| Risk ID | Hazard / failure mode | Impact | Initial | Implemented controls | Verification | Residual | External action |
|---|---|---|---:|---|---|---:|---|
| R-001 | Cross-subject or cross-study data exposure | Privacy breach and unsafe decision | 20 | Object/study authorization, assignment checks, pseudonymized models | Authorization and lifecycle suites | 5 | Independent penetration test |
| R-002 | Prohibited biomarker, treatment, or identifier reaches reviewer | Unblinding / privacy breach | 20 | Prohibited registry, import classification, mapping rejection | Privacy and mapping negative tests | 5 | DPO/clinical review of real extracts |
| R-003 | Missing evidence rendered as normal/negative | Incorrect adjudication | 20 | Explicit availability states and narrative safeguards | Missing-data and narrative scenarios | 6 | Clinical UAT on representative subjects |
| R-004 | Automated synthesis pre-adjudicates diagnosis | Human bias / protocol deviation | 16 | Separation of facts, deterministic findings, and human fields | Narrative and UI review | 6 | Clinical and ethics approval |
| R-005 | Sparse duplicate overwrites complete visit | Evidence loss | 16 | Merge/readiness policies and provenance | Duplicate-visit scenarios | 4 | Real-source reconciliation |
| R-006 | Corrected result loses lineage | Wrong evidence / inspection failure | 16 | Supersedes/correction identifiers and audit chain | Correction-lineage tests | 4 | Source-system contract approval |
| R-007 | Concurrent signing/finalization creates duplicate final record | Conflicting official record | 20 | State machine, locks, uniqueness and idempotency | Concurrency/lifecycle suite | 5 | PostgreSQL multi-replica test |
| R-008 | Signature does not bind complete content or assured identity | Invalid electronic record | 20 | Full-payload hash, meaning, session and MFA receipt | Signature tamper tests | 6 | Formal Part 11/Annex 11 assessment |
| R-009 | Filing reports success without destination integrity | Missing/tampered essential record | 20 | Authoritative read-back and SHA-256 receipt | Local adapter tamper tests and live qualification script | 5 | Qualified SharePoint tenant execution |
| R-010 | Demo bypass reaches production | Unauthorized access / synthetic data contamination | 20 | Fail-closed runtime policy and production UI/data separation | Runtime policy and deployment tests | 4 | Deployment configuration approval |
| R-011 | Brute force or abusive writes exhaust service | Account compromise / outage | 15 | Shared rate limits and lockout controls | Concurrent counter and security tests | 5 | WAF and alert validation |
| R-012 | Audit trail is altered or incomplete | Loss of accountability | 20 | Append-only listeners, reasoned events, hash/chain fields | Immutability and audit tests | 6 | Independent audit completeness sampling |
| R-013 | Backup exists but cannot restore | Prolonged loss / unrecoverable data | 20 | Encrypted backup, manifest verification, restore rehearsal | Backup script unit tests | 8 | Execute PostgreSQL restore and approve RTO/RPO |
| R-014 | Legal hold records are disposed | Regulatory/legal breach | 20 | Hold checks at request, approval, execution | Governance control tests | 4 | Records officer procedure approval |
| R-015 | Access persists beyond role need | Unauthorized disclosure/change | 16 | Snapshot-based review, no self-certification, automatic revocation | Governance control tests | 4 | Quarterly campaign execution |
| R-016 | Performance degrades under realistic load | Missed operational timelines / unsafe retry | 12 | Metrics, bounded workload runner, durable jobs | Smoke/load/soak protocol | 6 | Production-equivalent qualification |
| R-017 | Accessibility barrier prevents completion | Exclusion or workflow error | 12 | Semantic landmarks, focus, contrast, reduced motion | Axe suite and keyboard test | 4 | Manual WCAG/AT audit |
| R-018 | Dependency or infrastructure vulnerability is exploited | Confidentiality/integrity/availability loss | 20 | Lockfiles, security headers, secret policy | Dependency and penetration protocol | 8 | Resolve current dev audit findings and commission test |

## Risk acceptance rule

No initial critical risk is accepted solely because an automated test passes. QA and the accountable business/clinical owner must review evidence, deviations, and residual risk before pilot or production approval.
