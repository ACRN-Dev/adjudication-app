import pytest
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet

from main import app
from services.runtime_policy import (
    environment_name,
    legacy_unsafe_routes_enabled,
    validate_runtime_environment,
)


client = TestClient(app)


def test_environment_defaults_to_development(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert environment_name() == "development"


def test_legacy_routes_are_unconditionally_disabled_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENABLE_LEGACY_UNSAFE_ROUTES", "true")
    assert legacy_unsafe_routes_enabled() is False


def test_nonproduction_can_explicitly_disable_legacy_routes(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENABLE_LEGACY_UNSAFE_ROUTES", "false")
    assert legacy_unsafe_routes_enabled() is False


@pytest.mark.parametrize(
    "flag",
    ["ENABLE_DEMO_ACCOUNTS", "ENABLE_DEMO_DATA", "ENABLE_LEGACY_UNSAFE_ROUTES"],
)
def test_production_rejects_unsafe_feature_flags(monkeypatch, flag):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(flag, "true")
    with pytest.raises(RuntimeError, match=flag):
        validate_runtime_environment(database_is_fallback=False)


def test_production_rejects_database_fallback(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="fallback databases are prohibited"):
        validate_runtime_environment(database_is_fallback=True)


@pytest.mark.parametrize("required_key", ["RT_PSEUDONYM_SECRET", "RT_IDENTITY_ENCRYPTION_KEY"])
def test_production_requires_identity_protection_keys(monkeypatch, required_key):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RT_PSEUDONYM_SECRET", "p" * 48)
    monkeypatch.setenv("RT_IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.delenv(required_key, raising=False)
    with pytest.raises(RuntimeError, match=required_key):
        validate_runtime_environment(database_is_fallback=False)


def test_safe_production_runtime_policy_is_accepted(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    monkeypatch.setenv("ENABLE_DEMO_DATA", "false")
    monkeypatch.setenv("ENABLE_LEGACY_UNSAFE_ROUTES", "false")
    monkeypatch.setenv("RT_PSEUDONYM_SECRET", "p" * 48)
    monkeypatch.setenv("RT_IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("SESSION_HOURS", "12")
    monkeypatch.setenv("SESSION_IDLE_MINUTES", "30")
    monkeypatch.setenv("APP_BASE_URL", "https://adjudication.example.test")
    monkeypatch.setenv("METRICS_BEARER_TOKEN", "m" * 48)
    validate_runtime_environment(database_is_fallback=False)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("AUTH_COOKIE_SECURE", "false", "AUTH_COOKIE_SECURE"),
        ("AUTH_COOKIE_SAMESITE", "none", "AUTH_COOKIE_SAMESITE"),
        ("SESSION_IDLE_MINUTES", "120", "SESSION_IDLE_MINUTES"),
        ("APP_BASE_URL", "http://adjudication.example.test", "APP_BASE_URL"),
        ("CORS_EXTRA_ORIGINS", "*", "CORS_EXTRA_ORIGINS"),
    ],
)
def test_production_rejects_unsafe_browser_and_session_configuration(monkeypatch, name, value, message):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    monkeypatch.setenv("ENABLE_DEMO_DATA", "false")
    monkeypatch.setenv("ENABLE_LEGACY_UNSAFE_ROUTES", "false")
    monkeypatch.setenv("RT_PSEUDONYM_SECRET", "p" * 48)
    monkeypatch.setenv("RT_IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("SESSION_HOURS", "12")
    monkeypatch.setenv("SESSION_IDLE_MINUTES", "30")
    monkeypatch.setenv("APP_BASE_URL", "https://adjudication.example.test")
    monkeypatch.delenv("CORS_EXTRA_ORIGINS", raising=False)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        validate_runtime_environment(database_is_fallback=False)


@pytest.mark.parametrize(
    "path",
    [
        "/api/export/pdf/unknown-subject",
        "/api/export/csv",
        "/api/export/study-analysis",
    ],
)
def test_legacy_exports_fail_closed_when_production_policy_is_active(monkeypatch, path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "API route not found"}


def test_legacy_export_remains_available_in_explicit_demo_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "demo")
    monkeypatch.setenv("ENABLE_LEGACY_UNSAFE_ROUTES", "true")
    response = client.get("/api/export/csv")
    assert response.status_code == 200
