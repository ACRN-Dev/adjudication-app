# Performance, concurrency, and integration qualification

## Required environment

Run against an isolated, production-equivalent deployment backed by PostgreSQL. SQLite results are not production capacity evidence. Record the commit, database tier, replica count, region, test-data volume, and operator.

## Performance evidence

The runner sends only GET requests to explicitly listed routes and writes JSON evidence. Supply credentials through an approved secret mechanism.

```powershell
.\.venv\Scripts\python.exe backend\scripts\qualify_performance.py --base-url https://validation.example --profile load --email validation.monitor@example.org --password $env:ACRN_VALIDATION_PASSWORD --endpoint /health/ready --endpoint /api/auth/me --endpoint /api/monitor/operational-dashboard --output output/qualification/load.json
```

Defaults require at most 1% request errors, p95 at or below 1,000 ms, at least 1 request/second, and a correlation ID on every response. Override them only through an approved protocol. Execute `smoke`, `load`, then the two-hour `soak` profile and retain JSON plus infrastructure monitoring exports.

## Concurrency evidence

The backend suite tests simultaneous database-backed counter increments plus workflow uniqueness and idempotency. Production qualification must run with at least two application replicas and confirm shared counters, signature uniqueness, finalization, and audit sequencing in PostgreSQL.

## Integration evidence

For every EDC, eSource, LIMS, identity, notification, SharePoint, and eTMF connection retain: configuration version; redacted trace; positive transfer; retry; timeout; malformed payload rejection; duplicate/idempotency result; destination read-back; SHA-256 reconciliation for files; and named business-owner approval. The SharePoint adapter performs authoritative read-back before filing is complete. Live-tenant execution and owner approval remain external qualification activities.

Run the configured eTMF adapter contract check only in the approved validation library. It deliberately leaves a synthetic artifact and receipt as evidence:

```powershell
.\.venv\Scripts\python.exe backend\scripts\qualify_etmf.py --confirm-live-write VALIDATION-ONLY --study VALIDATION --output output/qualification/etmf.json
```

## Exit rule

Any threshold breach, unverified filing receipt, missing correlation ID, duplicate final record, lost update, or unexplained 5xx fails qualification. Open a deviation, remediate, and repeat the affected protocol.
