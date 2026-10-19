"""Fail-closed runtime policy for production deployments.

Prototype features remain available in explicitly non-production environments so
the existing demo and test harness can be used while the authoritative workflow
is rebuilt. Production never permits those paths, even if a feature flag is set
incorrectly.
"""

from __future__ import annotations

import os

from fastapi import HTTPException
from cryptography.fernet import Fernet


TRUTHY = {"1", "true", "yes", "on"}
PRODUCTION_NAMES = {"prod", "production"}


def _enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUTHY


def environment_name() -> str:
    """Return the normalized deployment environment name."""
    return (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()


def is_production() -> bool:
    return environment_name() in PRODUCTION_NAMES


def legacy_unsafe_routes_enabled() -> bool:
    """Whether prototype routers may be mounted.

    The production result is deliberately unconditional: an accidentally set
    flag cannot re-enable clinical bypass routes.
    """
    if is_production():
        return False
    return _enabled("ENABLE_LEGACY_UNSAFE_ROUTES", default=True)


def require_legacy_unsafe_route() -> None:
    """Request dependency for legacy endpoints sharing an otherwise safe router."""
    if not legacy_unsafe_routes_enabled():
        raise HTTPException(status_code=404, detail="API route not found")


def validate_runtime_environment(*, database_is_fallback: bool) -> None:
    """Reject production configurations that could weaken safety controls."""
    if not is_production():
        return

    violations: list[str] = []
    if database_is_fallback:
        violations.append("PostgreSQL is unavailable; fallback databases are prohibited")
    if _enabled("ENABLE_DEMO_ACCOUNTS"):
        violations.append("ENABLE_DEMO_ACCOUNTS must be false")
    if _enabled("ENABLE_DEMO_DATA"):
        violations.append("ENABLE_DEMO_DATA must be false")
    if _enabled("ENABLE_LEGACY_UNSAFE_ROUTES"):
        violations.append("ENABLE_LEGACY_UNSAFE_ROUTES must be false")
    if not _enabled("AUTH_COOKIE_SECURE"):
        violations.append("AUTH_COOKIE_SECURE must be true")
    if os.getenv("AUTH_COOKIE_SAMESITE", "").strip().lower() not in {"lax", "strict"}:
        violations.append("AUTH_COOKIE_SAMESITE must be lax or strict")
    try:
        session_hours = int(os.getenv("SESSION_HOURS", "12"))
        idle_minutes = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
        if not 1 <= session_hours <= 24:
            violations.append("SESSION_HOURS must be between 1 and 24")
        if not 5 <= idle_minutes <= 60 or idle_minutes >= session_hours * 60:
            violations.append("SESSION_IDLE_MINUTES must be between 5 and 60 and shorter than SESSION_HOURS")
    except ValueError:
        violations.append("SESSION_HOURS and SESSION_IDLE_MINUTES must be integers")
    base_url = os.getenv("APP_BASE_URL", "").strip()
    if not base_url.startswith("https://"):
        violations.append("APP_BASE_URL must use https")
    metrics_token = os.getenv("METRICS_BEARER_TOKEN", "").strip()
    if len(metrics_token) < 32:
        violations.append("METRICS_BEARER_TOKEN must contain at least 32 characters")
    extra_origins = [item.strip() for item in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if item.strip()]
    if any(origin == "*" or not origin.startswith("https://") for origin in extra_origins):
        violations.append("CORS_EXTRA_ORIGINS must contain only explicit https origins")
    pseudonym_secret = os.getenv("RT_PSEUDONYM_SECRET", "").strip()
    identity_key = os.getenv("RT_IDENTITY_ENCRYPTION_KEY", "").strip()
    if not pseudonym_secret:
        violations.append("RT_PSEUDONYM_SECRET is required")
    elif len(pseudonym_secret) < 32:
        violations.append("RT_PSEUDONYM_SECRET must contain at least 32 characters")
    if not identity_key:
        violations.append("RT_IDENTITY_ENCRYPTION_KEY is required")
    else:
        try:
            Fernet(identity_key.encode("ascii"))
        except (ValueError, TypeError, UnicodeEncodeError):
            violations.append("RT_IDENTITY_ENCRYPTION_KEY must be a valid Fernet key")

    if violations:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(violations))
