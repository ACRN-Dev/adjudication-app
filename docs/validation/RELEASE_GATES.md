# Release gates

| Gate | Required objective evidence | Failure condition |
|---|---|---|
| G0 Baseline | Approved URS, risk register, traceability, commit/image/dependency/migration identifiers | Uncontrolled or changing baseline |
| G1 Repository verification | Backend, frontend service, browser, axe, build, migration, static/security scans all recorded | Any unexplained failure or missing result |
| G2 Production configuration | Fail-closed startup, PostgreSQL, SSO/MFA, secrets, TLS, origins, metrics auth, demo disabled | Demo/fallback/insecure setting accepted |
| G3 Data and clinical | Real-source mapping reconciliation and pre-approved 25-scenario clinical expected results | Cross-subject data, prohibited data, missing/negative confusion, unsupported clinical statement |
| G4 Workflow and records | End-to-end Monitor through filing, signature/lock, audit, access review, retention/hold | Unauthorized transition, mutable final record, incomplete audit, hold bypass |
| G5 Reliability | Migration rehearsal, backup/restore RPO/RTO, multi-replica concurrency, load and soak | Restore failure, duplicate/lost update, threshold breach, sustained resource growth |
| G6 External systems | SSO, malware scanner, EDC/eSource/LIMS, notification, SharePoint/eTMF positive and negative contracts | Placeholder/manual path or missing read-back receipt |
| G7 Independent assurance | Penetration test, privacy review, Part 11/Annex 11 assessment, WCAG manual audit | Unaccepted Critical/High issue or missing accountable approval |
| G8 UAT and release | Named role UAT, deviations closed, residual risks accepted, rollback exercised, signed validation summary | Missing approval, open blocker, or untested rollback |

Production release is prohibited until every gate is passed in the target release baseline. A repository readiness score is not a substitute for these gates.
