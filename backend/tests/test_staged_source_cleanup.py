import uuid
from pathlib import Path

from models.longitudinal import RTImportBatch
from services.realtime_pipeline import purge_staged_source, staged_source_cleanup_enabled


def test_production_always_enables_staged_source_cleanup(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RT_DELETE_STAGED_SOURCE_AFTER_PROCESSING", "false")
    assert staged_source_cleanup_enabled() is True


def test_purge_staged_source_deletes_file_and_clears_persisted_path():
    staging = Path(__file__).parents[1] / ".rt-staging"
    staging.mkdir(exist_ok=True)
    path = staging / f"cleanup-{uuid.uuid4().hex}.csv"
    path.write_bytes(b"MRN,Screening #\nexample,example\n")
    batch = RTImportBatch(
        filename=path.name,
        checksum=uuid.uuid4().hex,
        file_size=path.stat().st_size,
        uploaded_by="cleanup-test@acrnhealth.com",
        source_path=str(path),
    )
    assert purge_staged_source(batch) is True
    assert batch.source_path is None
    assert not path.exists()


def test_purge_staged_source_refuses_path_outside_staging_directory():
    temp_root = Path(__file__).parents[1] / ".pytest-tmp-run"
    temp_root.mkdir(exist_ok=True)
    path = temp_root / f"outside-{uuid.uuid4().hex}.csv"
    path.write_bytes(b"sensitive")
    batch = RTImportBatch(
        filename=path.name,
        checksum=uuid.uuid4().hex,
        file_size=path.stat().st_size,
        uploaded_by="cleanup-test@acrnhealth.com",
        source_path=str(path),
    )
    try:
        try:
            purge_staged_source(batch)
            assert False, "cleanup should reject paths outside .rt-staging"
        except ValueError as exc:
            assert "outside the RealTime staging directory" in str(exc)
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)
