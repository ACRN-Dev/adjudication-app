# Backup, restore, and disaster-recovery runbook

## Control objective

Production must produce checksum-verifiable PostgreSQL custom-format backups on an approved encrypted target. A restore is considered qualified only after restoration into an isolated validation database, critical-table checks, audit-integrity checks, and retention of the generated evidence JSON.

## Backup

Set the standard `DB_*` connection variables and `BACKUP_STORAGE_ENCRYPTED=true`, then run:

```text
python backend/scripts/backup_restore.py backup --output-dir <approved-encrypted-backup-path>
```

Retain both the `.dump` and `.manifest.json` files. Alert if no successful manifest is produced within the approved RPO. Copying a dump without its manifest is not a valid backup.

## Integrity verification

```text
python backend/scripts/backup_restore.py verify --manifest <backup.dump.manifest.json>
```

This checks the exact byte length, SHA-256 digest, manifest version, and PostgreSQL archive catalog.

## Restore rehearsal

Provision an empty, isolated PostgreSQL database. Set `RESTORE_DB_HOST`, `RESTORE_DB_PORT`, `RESTORE_DB_NAME`, `RESTORE_DB_USER`, `RESTORE_DB_PASSWORD`, and `RESTORE_DB_SSL_MODE`. The tool refuses to restore over the source database and requires an exact target-name confirmation.

```text
python backend/scripts/backup_restore.py restore-rehearsal --manifest <manifest> --confirm-target <RESTORE_DB_NAME> --evidence output/validation/postgres-restore.json
```

Record the measured restore time as RTO evidence and the backup age as RPO evidence. Review restored counts against the source reconciliation report. Destroy the isolated rehearsal database through the approved infrastructure process after QA accepts the evidence.

## Required external evidence

- backup scheduler and missed-backup alert screenshot/export;
- encrypted-storage and access-policy evidence;
- at least one successful quarterly restore evidence JSON;
- source-versus-restored reconciliation approval;
- documented RPO/RTO acceptance and disaster-recovery owner signature;
- failure-injection record covering corrupt backup, unavailable target, and credential failure.
