"""Request correlation, shared rate limiting, and scrapeable service metrics."""
from __future__ import annotations

import hashlib
import os
import threading
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from models.auth import ApiRateLimitBucket
from services.runtime_policy import is_production


RATE_POLICIES = (
    ("login", "POST", "/api/auth/login", "RATE_LIMIT_LOGIN", 10, 60),
    ("upload", "POST", "/api/realtime/upload", "RATE_LIMIT_UPLOAD", 12, 3600),
    ("signature", "POST", "/api/adjudication/", "RATE_LIMIT_SIGNATURE", 30, 60),
    ("export", "GET", "/api/export/", "RATE_LIMIT_EXPORT", 20, 3600),
    ("query", "POST", "/api/realtime/", "RATE_LIMIT_CLINICAL_WRITE", 60, 60),
    ("admin", "POST", "/api/admin/", "RATE_LIMIT_ADMIN_WRITE", 60, 60),
)


def rate_limits_enabled():
    return is_production() or os.getenv("RATE_LIMIT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def matching_policy(method: str, path: str):
    for action, required_method, prefix, env_name, default_limit, seconds in RATE_POLICIES:
        if method == required_method and path.startswith(prefix):
            return action, max(1, int(os.getenv(env_name, str(default_limit)))), seconds
    return None


def request_subject(request) -> str:
    session_token = request.cookies.get("acrn_demo_session")
    source = f"session:{session_token}" if session_token else f"ip:{request.client.host if request.client else 'unknown'}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def consume_rate_limit(db, *, subject_hash: str, action: str, limit: int, window_seconds: int, now=None):
    now = now or datetime.utcnow()
    epoch = int(now.timestamp())
    window_epoch = epoch - (epoch % window_seconds)
    window_start = datetime.utcfromtimestamp(window_epoch)
    expires_at = window_start + timedelta(seconds=window_seconds * 2)
    identity = {
        "subject_hash": subject_hash, "action": action, "window_started_at": window_start,
    }
    # Increment in SQL, not by read/modify/write, so simultaneous application
    # nodes cannot overwrite one another's counters.
    updated = db.query(ApiRateLimitBucket).filter_by(**identity).update(
        {ApiRateLimitBucket.request_count: ApiRateLimitBucket.request_count + 1,
         ApiRateLimitBucket.expires_at: expires_at}, synchronize_session=False,
    )
    if not updated:
        row = ApiRateLimitBucket(
            subject_hash=subject_hash, action=action, window_started_at=window_start,
            request_count=1, expires_at=expires_at,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            db.query(ApiRateLimitBucket).filter_by(**identity).update(
                {ApiRateLimitBucket.request_count: ApiRateLimitBucket.request_count + 1,
                 ApiRateLimitBucket.expires_at: expires_at}, synchronize_session=False,
            )
            db.commit()
    else:
        db.commit()
    row = db.query(ApiRateLimitBucket).filter_by(**identity).one()
    retry_after = max(1, int((window_start + timedelta(seconds=window_seconds) - now).total_seconds()))
    return row.request_count <= limit, retry_after, row.request_count


class RequestMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.requests = Counter()
        self.duration_seconds = defaultdict(float)
        self.in_flight = 0
        self.rate_limited = Counter()

    def start(self):
        with self._lock:
            self.in_flight += 1

    def finish(self, method, route, status, duration):
        route = route.replace('"', '')[:180]
        key = (method, route, str(status))
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
            self.requests[key] += 1
            self.duration_seconds[(method, route)] += duration

    def limited(self, action):
        with self._lock:
            self.rate_limited[action] += 1

    def render(self):
        with self._lock:
            lines = [
                "# HELP acrn_http_requests_total HTTP requests processed.",
                "# TYPE acrn_http_requests_total counter",
            ]
            for (method, route, status), count in sorted(self.requests.items()):
                lines.append(f'acrn_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {count}')
            lines.extend(["# HELP acrn_http_request_duration_seconds_sum Accumulated request duration.", "# TYPE acrn_http_request_duration_seconds_sum counter"])
            for (method, route), value in sorted(self.duration_seconds.items()):
                lines.append(f'acrn_http_request_duration_seconds_sum{{method="{method}",route="{route}"}} {value:.6f}')
            lines.extend(["# HELP acrn_http_requests_in_flight Requests currently executing.", "# TYPE acrn_http_requests_in_flight gauge", f"acrn_http_requests_in_flight {self.in_flight}"])
            for action, count in sorted(self.rate_limited.items()):
                lines.append(f'acrn_rate_limited_total{{action="{action}"}} {count}')
            return "\n".join(lines) + "\n"


metrics = RequestMetrics()
