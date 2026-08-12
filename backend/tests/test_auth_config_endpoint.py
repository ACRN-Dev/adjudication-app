import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import app
from conftest import TestingSession

client = TestClient(app)


def test_auth_config_reports_demo_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_DEMO_ACCOUNTS", raising=False)
    r = client.get("/api/auth/config")
    assert r.status_code == 200
    assert r.json() == {"demo_enabled": False}


def test_auth_config_reports_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    r = client.get("/api/auth/config")
    assert r.json() == {"demo_enabled": True}
