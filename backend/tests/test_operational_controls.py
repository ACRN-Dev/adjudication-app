from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from conftest import TestingSession
from main import app
from models.auth import ApiRateLimitBucket
from database import Base
from services.operational_controls import consume_rate_limit, metrics


def test_shared_rate_limit_bucket_blocks_after_configured_limit():
    db = TestingSession()
    try:
        now = datetime(2026, 10, 19, 10, 0, 5)
        outcomes = [
            consume_rate_limit(
                db, subject_hash="a" * 64, action="test", limit=2,
                window_seconds=60, now=now,
            )
            for _ in range(3)
        ]
        assert [item[0] for item in outcomes] == [True, True, False]
        assert outcomes[-1][2] == 3
        assert db.query(ApiRateLimitBucket).filter_by(action="test").count() == 1
    finally:
        db.close()


def test_shared_rate_limit_counter_has_no_lost_updates_under_concurrency():
    now = datetime(2026, 10, 19, 11, 0, 5)
    subject = "c" * 64
    directory = Path("output") / "test-temp"
    directory.mkdir(parents=True, exist_ok=True)
    database_path = (directory / f"rate-limit-{uuid.uuid4().hex}.db").resolve()
    engine = create_engine(f"sqlite:///{database_path.as_posix()}",
                           connect_args={"check_same_thread": False, "timeout": 30})
    try:
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def consume(_):
            db = sessions()
            try:
                return consume_rate_limit(db, subject_hash=subject, action="concurrent", limit=100,
                                          window_seconds=60, now=now)[2]
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(consume, range(20)))
        db = sessions()
        try:
            assert db.query(ApiRateLimitBucket).filter_by(subject_hash=subject, action="concurrent").one().request_count == 20
        finally:
            db.close()
    finally:
        engine.dispose()
        database_path.unlink(missing_ok=True)


def test_every_response_has_correlation_identifier(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert len(response.headers["x-correlation-id"]) == 36


def test_metrics_are_scrapeable_and_bounded_to_route_templates(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    client = TestClient(app)
    client.get("/api/auth/config")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "acrn_http_requests_total" in response.text
    assert 'route="/api/auth/config"' in response.text


def test_production_metrics_require_bearer_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("METRICS_BEARER_TOKEN", "metrics-secret-which-is-long-enough")
    client = TestClient(app)
    assert client.get("/metrics").status_code == 401
    allowed = client.get("/metrics", headers={"Authorization": "Bearer metrics-secret-which-is-long-enough"})
    assert allowed.status_code == 200
