"""Qualified PostgreSQL backup, integrity verification, and restore rehearsal CLI.

The CLI never accepts database passwords on the command line. Source connection
settings use DB_* variables; a restore rehearsal uses RESTORE_DB_* variables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2


CRITICAL_TABLES = (
    "portal_users", "participants", "adjudication_visits", "adjudication_records",
    "signed_case_artifacts", "committee_decisions", "committee_meetings",
    "longitudinal_participants", "canonical_observations", "longitudinal_audit_events",
)


def _connection(prefix="DB"):
    required = {name: os.getenv(f"{prefix}_{name}", "").strip() for name in ("HOST", "PORT", "NAME", "USER", "PASSWORD")}
    missing = [f"{prefix}_{name}" for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing database settings: {', '.join(missing)}")
    required["SSLMODE"] = os.getenv(f"{prefix}_SSL_MODE", "require")
    return required


def _tool(name):
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Required PostgreSQL utility is not installed: {name}")
    return resolved


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pg_env(settings):
    env = os.environ.copy()
    env["PGPASSWORD"] = settings["PASSWORD"]
    env["PGSSLMODE"] = settings["SSLMODE"]
    return env


def create_backup(output_dir: Path):
    if os.getenv("ENVIRONMENT", "development").lower() in {"prod", "production"} and os.getenv("BACKUP_STORAGE_ENCRYPTED", "false").lower() != "true":
        raise RuntimeError("Production backups require BACKUP_STORAGE_ENCRYPTED=true on the approved encrypted target")
    source = _connection("DB")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump = output_dir / f"acrn-{source['NAME']}-{stamp}.dump"
    command = [
        _tool("pg_dump"), "--format=custom", "--no-owner", "--no-acl",
        "--host", source["HOST"], "--port", source["PORT"], "--username", source["USER"],
        "--dbname", source["NAME"], "--file", str(dump),
    ]
    started = time.perf_counter()
    subprocess.run(command, env=_pg_env(source), check=True, capture_output=True)
    if not dump.is_file() or dump.stat().st_size == 0:
        raise RuntimeError("pg_dump completed without a non-empty backup artifact")
    subprocess.run([_tool("pg_restore"), "--list", str(dump)], check=True, capture_output=True)
    manifest = {
        "format_version": "ACRN-BACKUP-1", "created_at": datetime.now(timezone.utc).isoformat(),
        "database": source["NAME"], "database_host_hash": hashlib.sha256(source["HOST"].encode()).hexdigest(),
        "artifact": dump.name, "size_bytes": dump.stat().st_size, "sha256": _sha256(dump),
        "storage_encrypted": os.getenv("BACKUP_STORAGE_ENCRYPTED", "false").lower() == "true",
        "pg_dump_seconds": round(time.perf_counter() - started, 3),
    }
    manifest_path = Path(str(dump) + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def verify_backup(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != "ACRN-BACKUP-1":
        raise RuntimeError("Unsupported backup manifest format")
    artifact = manifest_path.parent / manifest["artifact"]
    if not artifact.is_file() or artifact.stat().st_size != manifest["size_bytes"]:
        raise RuntimeError("Backup artifact is missing or has the wrong size")
    if _sha256(artifact) != manifest["sha256"]:
        raise RuntimeError("Backup checksum verification failed")
    subprocess.run([_tool("pg_restore"), "--list", str(artifact)], check=True, capture_output=True)
    return manifest, artifact


def restore_rehearsal(manifest_path: Path, confirm_target: str, evidence_path: Path):
    manifest, artifact = verify_backup(manifest_path)
    source = _connection("DB")
    target = _connection("RESTORE_DB")
    if confirm_target != target["NAME"]:
        raise RuntimeError("--confirm-target must exactly match RESTORE_DB_NAME")
    if (source["HOST"], source["PORT"], source["NAME"]) == (target["HOST"], target["PORT"], target["NAME"]):
        raise RuntimeError("Restore rehearsal target must not be the source database")
    started = time.perf_counter()
    command = [
        _tool("pg_restore"), "--clean", "--if-exists", "--exit-on-error", "--no-owner", "--no-acl",
        "--host", target["HOST"], "--port", target["PORT"], "--username", target["USER"],
        "--dbname", target["NAME"], str(artifact),
    ]
    subprocess.run(command, env=_pg_env(target), check=True, capture_output=True)
    counts = {}
    with psycopg2.connect(
        host=target["HOST"], port=target["PORT"], dbname=target["NAME"], user=target["USER"],
        password=target["PASSWORD"], sslmode=target["SSLMODE"],
    ) as connection:
        with connection.cursor() as cursor:
            for table in CRITICAL_TABLES:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                counts[table] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM longitudinal_audit_events WHERE chain_sequence IS NULL OR integrity_version IS NULL")
            invalid_audit_rows = cursor.fetchone()[0]
    completed = datetime.now(timezone.utc)
    backup_created = datetime.fromisoformat(manifest["created_at"])
    evidence = {
        "qualification": "POSTGRESQL_RESTORE_REHEARSAL", "status": "PASS" if invalid_audit_rows == 0 else "FAIL",
        "completed_at": completed.isoformat(), "source_database": manifest["database"],
        "target_database": target["NAME"], "backup_sha256": manifest["sha256"],
        "restore_seconds": round(time.perf_counter() - started, 3),
        "recovery_point_age_seconds": round((completed - backup_created).total_seconds(), 3),
        "critical_table_counts": counts, "invalid_audit_rows": invalid_audit_rows,
    }
    evidence_path = evidence_path.resolve()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if evidence["status"] != "PASS":
        raise RuntimeError("Restored audit integrity checks failed")
    return evidence_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup"); backup.add_argument("--output-dir", type=Path, required=True)
    verify = sub.add_parser("verify"); verify.add_argument("--manifest", type=Path, required=True)
    restore = sub.add_parser("restore-rehearsal")
    restore.add_argument("--manifest", type=Path, required=True)
    restore.add_argument("--confirm-target", required=True)
    restore.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "backup": result = create_backup(args.output_dir)
    elif args.command == "verify": result = verify_backup(args.manifest)[1]
    else: result = restore_rehearsal(args.manifest, args.confirm_target, args.evidence)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
