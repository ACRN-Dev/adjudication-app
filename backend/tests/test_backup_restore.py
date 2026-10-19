import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import backup_restore


def _source_env(monkeypatch):
    for key, value in {
        "DB_HOST": "source-db", "DB_PORT": "5432", "DB_NAME": "acrn",
        "DB_USER": "backup", "DB_PASSWORD": "secret", "DB_SSL_MODE": "require",
    }.items():
        monkeypatch.setenv(key, value)


def _fake_run(command, **_kwargs):
    if "--file" in command:
        Path(command[command.index("--file") + 1]).write_bytes(b"qualified-postgresql-dump")
    return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()


def test_backup_creates_checksum_manifest_and_verifies_archive(monkeypatch, tmp_path):
    _source_env(monkeypatch)
    monkeypatch.setenv("BACKUP_STORAGE_ENCRYPTED", "true")
    with patch.object(backup_restore.shutil, "which", side_effect=lambda name: name), patch.object(backup_restore.subprocess, "run", side_effect=_fake_run):
        manifest_path = backup_restore.create_backup(tmp_path)
        manifest, artifact = backup_restore.verify_backup(manifest_path)
    assert manifest["format_version"] == "ACRN-BACKUP-1"
    assert manifest["storage_encrypted"] is True
    assert artifact.read_bytes() == b"qualified-postgresql-dump"
    assert len(manifest["sha256"]) == 64


def test_backup_verification_detects_byte_tampering(monkeypatch, tmp_path):
    _source_env(monkeypatch)
    with patch.object(backup_restore.shutil, "which", side_effect=lambda name: name), patch.object(backup_restore.subprocess, "run", side_effect=_fake_run):
        manifest_path = backup_restore.create_backup(tmp_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        (tmp_path / manifest["artifact"]).write_bytes(b"tampered")
        with pytest.raises(RuntimeError, match="wrong size|checksum"):
            backup_restore.verify_backup(manifest_path)


def test_production_backup_requires_approved_encrypted_target(monkeypatch, tmp_path):
    _source_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("BACKUP_STORAGE_ENCRYPTED", "false")
    with pytest.raises(RuntimeError, match="BACKUP_STORAGE_ENCRYPTED"):
        backup_restore.create_backup(tmp_path)


def test_restore_rehearsal_refuses_source_database(monkeypatch, tmp_path):
    _source_env(monkeypatch)
    for suffix, value in {
        "HOST": "source-db", "PORT": "5432", "NAME": "acrn",
        "USER": "restore", "PASSWORD": "secret", "SSL_MODE": "require",
    }.items():
        monkeypatch.setenv(f"RESTORE_DB_{suffix}", value)
    with patch.object(backup_restore.shutil, "which", side_effect=lambda name: name), patch.object(backup_restore.subprocess, "run", side_effect=_fake_run):
        manifest_path = backup_restore.create_backup(tmp_path)
        with pytest.raises(RuntimeError, match="must not be the source"):
            backup_restore.restore_rehearsal(manifest_path, "acrn", tmp_path / "evidence.json")


def test_restore_rehearsal_requires_exact_target_confirmation(monkeypatch, tmp_path):
    _source_env(monkeypatch)
    for suffix, value in {
        "HOST": "restore-db", "PORT": "5432", "NAME": "acrn_restore",
        "USER": "restore", "PASSWORD": "secret", "SSL_MODE": "require",
    }.items():
        monkeypatch.setenv(f"RESTORE_DB_{suffix}", value)
    with patch.object(backup_restore.shutil, "which", side_effect=lambda name: name), patch.object(backup_restore.subprocess, "run", side_effect=_fake_run):
        manifest_path = backup_restore.create_backup(tmp_path)
        with pytest.raises(RuntimeError, match="confirm-target"):
            backup_restore.restore_rehearsal(manifest_path, "wrong_database", tmp_path / "evidence.json")
