# Microsoft SSO Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Microsoft Entra ID single sign-on as the login path for the real dev/prod servers, and make it actually secure the Admin and Monitor portals (not just the login screen) by deriving their authorization from the session instead of client-supplied headers.

**Architecture:** A backend-driven OAuth2 Authorization Code flow using the `msal` Python library (confidential client) issues the exact same session cookie the app already uses for demo login. `PortalUser` gains two columns — `portal_role` (the Admin/Monitor sub-role, e.g. `TECHNICAL_ADMIN`) and `study_scope` — so an Admin can pre-provision real users with everything the Admin/Monitor portals need to authorize them from the session alone.

**Tech Stack:** FastAPI, SQLAlchemy, `msal` (new dependency), React (no new frontend dependency — plain browser redirect).

## Global Constraints

- Demo accounts keep working exactly as today when `ENABLE_DEMO_ACCOUNTS=true` (local/offline dev). When `false` (real dev/prod servers), only a valid Microsoft SSO session grants access — the `X-Demo-*` headers are never trusted.
- No JIT auto-provisioning. An unregistered email is rejected with a clear message; an Admin must create the `PortalUser` row first via `/api/auth/users`.
- No Entra App Roles or Security Groups — role/sub-role mapping lives entirely in `PortalUser.role` / `PortalUser.portal_role`, set by an Admin.
- The session cookie name (`acrn_demo_session`) is **not** renamed in this plan — purely cosmetic, descoped to limit risk of touching every file that references it.
- The existing hardcoded `X-Demo-Role`/`X-Study-Scope` values sent by `src/admin/AdminPortal.jsx`, `src/monitor/MonitorPortal.jsx`, and `src/services/realtimeApi.js` are **left as-is** in this plan. Once Task 5/6 land, those headers are only ever consulted when `ENABLE_DEMO_ACCOUNTS=true`, so leaving them doesn't reopen the gap this plan closes — it's cosmetic cleanup, descoped to avoid risky edits to dense, unfamiliar frontend files for no security benefit.
- **Deployment note (not a code task, but required before this feature works on the real servers):** `Base.metadata.create_all()` only creates *missing* tables — it never alters an existing table's columns. The real dev/prod Postgres databases already have a `portal_users` table, so Task 1's new columns and relaxed `NOT NULL` constraint will **not** appear there automatically on redeploy. The migration SQL file this plan adds (`backend/migrations/versions/20260812_05_sso_login.sql`) must be run manually against each server's Postgres database (e.g. `psql "$DATABASE_URL" -f backend/migrations/versions/20260812_05_sso_login.sql`) before that server's SSO login path will work. Local SQLite (the offline fallback) doesn't need this — delete `backend/acrn_demo.db` to force a fresh schema if you hit a `NOT NULL` error locally.

---

### Task 1: `PortalUser` schema — `portal_role`, `study_scope`, nullable `password_hash`

**Files:**
- Modify: `backend/models/auth.py`
- Create: `backend/migrations/versions/20260812_05_sso_login.sql`
- Test: `backend/tests/test_portal_user_sso_fields.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `PortalUser.portal_role` (nullable `String(40)`, one of the Admin sub-roles in `services.admin_security.ADMIN_ROLES` or Monitor's `services.monitor_security.ROLES`, or `None` for `ADJUDICATOR`), `PortalUser.study_scope` (nullable `String(500)`, comma-separated study codes or `"*"`, defaults to `"*"`), `PortalUser.password_hash` now nullable. Every later task in this plan depends on these three fields existing on the model.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_portal_user_sso_fields.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models.auth import PortalUser

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def test_sso_managed_user_has_no_password_but_keeps_portal_role_and_scope():
    db = TestingSession()
    user = PortalUser(
        email="sso.admin@acrnhealth.com",
        display_name="SSO Admin",
        password_hash=None,
        role="ADMIN",
        portal_role="TECHNICAL_ADMIN",
        study_scope="PROTECT-Africa",
    )
    db.add(user)
    db.commit()
    fetched = db.query(PortalUser).filter_by(email="sso.admin@acrnhealth.com").first()
    assert fetched.password_hash is None
    assert fetched.portal_role == "TECHNICAL_ADMIN"
    assert fetched.study_scope == "PROTECT-Africa"
    db.close()


def test_study_scope_defaults_to_wildcard_and_portal_role_defaults_to_none():
    db = TestingSession()
    user = PortalUser(
        email="plain.adjudicator@acrnhealth.com",
        display_name="Plain Adjudicator",
        password_hash="some-hash",
        role="ADJUDICATOR",
    )
    db.add(user)
    db.commit()
    fetched = db.query(PortalUser).filter_by(email="plain.adjudicator@acrnhealth.com").first()
    assert fetched.portal_role is None
    assert fetched.study_scope == "*"
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, Python 3.12 environment with `requirements.txt` installed):
```
python -m pytest tests/test_portal_user_sso_fields.py -v
```
Expected: FAIL — `TypeError: 'portal_role' is an invalid keyword argument for PortalUser` (or similar, since the column doesn't exist yet).

- [ ] **Step 3: Add the columns to `PortalUser`**

In `backend/models/auth.py`, the current class reads:

```python
class PortalUser(Base):
    __tablename__ = "portal_users"
    id = Column(String(36), primary_key=True, default=uid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(160), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ACTIVE", index=True)
    is_demo_account = Column(Boolean, nullable=False, default=True, index=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Replace it with:

```python
class PortalUser(Base):
    __tablename__ = "portal_users"
    id = Column(String(36), primary_key=True, default=uid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(160), nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(30), nullable=False, index=True)
    portal_role = Column(String(40), nullable=True)
    study_scope = Column(String(500), nullable=True, default="*")
    status = Column(String(30), nullable=False, default="ACTIVE", index=True)
    is_demo_account = Column(Boolean, nullable=False, default=True, index=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
python -m pytest tests/test_portal_user_sso_fields.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Run the full existing backend suite to confirm no regression**

Run (from `backend/`):
```
python -m pytest tests -v
```
Expected: all tests pass unchanged (the two new columns are nullable/defaulted, and `password_hash` staying populated for every existing code path — demo seeding, admin creation — means no existing row or code path is affected).

- [ ] **Step 6: Write the migration SQL file**

Create `backend/migrations/versions/20260812_05_sso_login.sql`:

```sql
ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS portal_role VARCHAR(40);
ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS study_scope VARCHAR(500) DEFAULT '*';
ALTER TABLE portal_users ALTER COLUMN password_hash DROP NOT NULL;
```

- [ ] **Step 7: Commit**

```bash
git add backend/models/auth.py backend/tests/test_portal_user_sso_fields.py backend/migrations/versions/20260812_05_sso_login.sql
git commit -m "feat: add portal_role and study_scope to PortalUser, allow SSO-managed users without a password"
```

---

### Task 2: `msal` dependency and `GET /api/auth/config`

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/api/auth.py`
- Test: `backend/tests/test_auth_config_endpoint.py`

**Interfaces:**
- Consumes: `ENABLE_DEMO_ACCOUNTS` env var (already read elsewhere in the codebase).
- Produces: `GET /api/auth/config` → `{"demo_enabled": bool}`, unauthenticated. Task 7 (frontend) depends on this exact endpoint path and response shape.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_auth_config_endpoint.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
python -m pytest tests/test_auth_config_endpoint.py -v
```
Expected: FAIL with 404 (route doesn't exist yet).

- [ ] **Step 3: Add `msal` to requirements**

In `backend/requirements.txt`, the file currently ends with:
```
pytest==8.2.2
pytest-asyncio==0.23.7
```

Append one line so it reads:
```
pytest==8.2.2
pytest-asyncio==0.23.7
msal==1.28.0
```

Install it locally too so later steps in this task and Task 3 can run: `pip install msal==1.28.0` (from the same environment used for the other backend tests).

- [ ] **Step 4: Add the `/config` endpoint**

In `backend/api/auth.py`, the file currently starts with:

```python
"""Login, logout and demo account management endpoints."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, INACTIVE, ROLE_ADMIN, audit_auth, current_user, default_password,
    hash_password, identity_from_user, login as auth_login, logout as auth_logout,
    require_role, seed_demo_accounts, normalize_email,
)

router = APIRouter()
```

Replace it with (adding `import os` and the `/config` route right after `router = APIRouter()`):

```python
"""Login, logout and demo account management endpoints."""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, INACTIVE, ROLE_ADMIN, audit_auth, current_user, default_password,
    hash_password, identity_from_user, login as auth_login, logout as auth_logout,
    require_role, seed_demo_accounts, normalize_email,
)

router = APIRouter()


@router.get("/config")
def auth_config():
    return {"demo_enabled": os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true"}
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```
python -m pytest tests/test_auth_config_endpoint.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Run the full existing backend suite to confirm no regression**

Run:
```
python -m pytest tests -v
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/api/auth.py backend/tests/test_auth_config_endpoint.py
git commit -m "feat: add msal dependency and GET /api/auth/config endpoint"
```

---

### Task 3: SSO login and callback endpoints

**Files:**
- Modify: `backend/services/auth_service.py`
- Modify: `backend/api/auth.py`
- Test: `backend/tests/test_sso_login.py`

**Interfaces:**
- Consumes: `PortalUser.portal_role`/`study_scope` (Task 1), `msal` (Task 2), env vars `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `APP_BASE_URL` (new, read directly via `os.environ`/`os.getenv` — no config-loading module exists in this codebase to extend).
- Produces: `GET /api/auth/sso/login`, `GET /api/auth/sso/callback` — Task 5 and 6 don't call these directly but rely on the session cookie they establish being indistinguishable from a password-login session. `auth_service.issue_session(db, user, response, request, event_type)` — a new public function other code can reuse for any non-password login path.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sso_login.py`:

```python
import hashlib
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models.auth import AuthAuditEvent, PortalUser
from services.auth_service import ACTIVE

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def _set_sso_env():
    os.environ["ENTRA_CLIENT_ID"] = "test-client-id"
    os.environ["ENTRA_CLIENT_SECRET"] = "test-secret"
    os.environ["ENTRA_TENANT_ID"] = "test-tenant-id"
    os.environ["APP_BASE_URL"] = "https://adjudication-test.acrncloud.com"


def test_sso_login_redirects_to_microsoft_with_state_cookie():
    _set_sso_env()
    r = client.get("/api/auth/sso/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "login.microsoftonline.com" in r.headers["location"]
    assert "acrn_sso_state" in r.cookies


def test_sso_callback_rejects_state_mismatch():
    _set_sso_env()
    r = client.get("/api/auth/sso/callback?code=abc&state=wrong", cookies={"acrn_sso_state": "right"})
    assert r.status_code == 400


@patch("api.auth._sso_app")
def test_sso_callback_creates_session_for_registered_user(mock_sso_app):
    _set_sso_env()
    db = TestingSession()
    db.add(PortalUser(
        email="ssoadmin@acrnhealth.com", display_name="SSO Admin", password_hash=None,
        role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()

    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {"preferred_username": "ssoadmin@acrnhealth.com", "name": "SSO Admin"}
    }
    mock_sso_app.return_value = mock_client

    r = client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "acrn_demo_session" in r.cookies

    db = TestingSession()
    assert db.query(AuthAuditEvent).filter_by(event_type="SSO_LOGIN_SUCCESS").count() == 1
    db.close()


@patch("api.auth._sso_app")
def test_sso_callback_rejects_unregistered_email(mock_sso_app):
    _set_sso_env()
    mock_client = MagicMock()
    mock_client.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {"preferred_username": "unknown.person@acrnhealth.com", "name": "Unknown Person"}
    }
    mock_sso_app.return_value = mock_client

    r = client.get(
        "/api/auth/sso/callback?code=abc123&state=xyz",
        cookies={"acrn_sso_state": "xyz"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "sso_error=not_registered" in r.headers["location"]
    assert "acrn_demo_session" not in r.cookies
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
python -m pytest tests/test_sso_login.py -v
```
Expected: FAIL — 404s on `/api/auth/sso/login` and `/api/auth/sso/callback` (routes don't exist yet).

- [ ] **Step 3: Extract a reusable session-issuance helper in `auth_service.py`**

In `backend/services/auth_service.py`, the current `login()` function reads:

```python
def login(db: Session, email: str, password: str, response: Response, request: Request) -> dict:
    normalized = normalize_email(email)
    generic = HTTPException(401, "Invalid email or password.")
    user = db.query(PortalUser).filter_by(email=normalized).first()
    now = datetime.utcnow()
    if not user:
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", request=request, details={"email_hash": hashlib.sha256(normalized.encode()).hexdigest()})
        db.commit()
        raise generic
    if user.status != ACTIVE or (user.locked_until and user.locked_until > now):
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request, reason="Account inactive or locked")
        db.commit()
        raise generic
    if not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= LOCK_AFTER:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            audit_auth(db, "ACCOUNT_LOCK", "SUCCESS", affected=user, request=request, reason="Repeated failed login attempts")
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request)
        db.commit()
        raise generic
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    raw_token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=_hash_token(raw_token),
        user_id=user.id,
        expires_at=now + timedelta(hours=SESSION_HOURS),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else ""),
        ip_address=(request.client.host if request and request.client else ""),
    ))
    audit_auth(db, "LOGIN_SUCCESS", "SUCCESS", actor=user, affected=user, request=request)
    db.commit()
    response.set_cookie(
        AUTH_COOKIE,
        raw_token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=SESSION_HOURS * 3600,
        path="/",
    )
    return _public_user(user)
```

Replace it with (extracting the session-issuance tail into `issue_session`, and guarding against a `None` `password_hash` so an SSO-managed account can never be logged into via the password form):

```python
def issue_session(db: Session, user: PortalUser, response: Response, request: Optional[Request], event_type: str = "LOGIN_SUCCESS") -> dict:
    now = datetime.utcnow()
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    raw_token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=_hash_token(raw_token),
        user_id=user.id,
        expires_at=now + timedelta(hours=SESSION_HOURS),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else ""),
        ip_address=(request.client.host if request and request.client else ""),
    ))
    audit_auth(db, event_type, "SUCCESS", actor=user, affected=user, request=request)
    db.commit()
    response.set_cookie(
        AUTH_COOKIE,
        raw_token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=SESSION_HOURS * 3600,
        path="/",
    )
    return _public_user(user)


def login(db: Session, email: str, password: str, response: Response, request: Request) -> dict:
    normalized = normalize_email(email)
    generic = HTTPException(401, "Invalid email or password.")
    user = db.query(PortalUser).filter_by(email=normalized).first()
    now = datetime.utcnow()
    if not user:
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", request=request, details={"email_hash": hashlib.sha256(normalized.encode()).hexdigest()})
        db.commit()
        raise generic
    if user.status != ACTIVE or (user.locked_until and user.locked_until > now):
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request, reason="Account inactive or locked")
        db.commit()
        raise generic
    if not user.password_hash or not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= LOCK_AFTER:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            audit_auth(db, "ACCOUNT_LOCK", "SUCCESS", affected=user, request=request, reason="Repeated failed login attempts")
        audit_auth(db, "LOGIN_FAILURE", "FAILURE", affected=user, request=request)
        db.commit()
        raise generic
    return issue_session(db, user, response, request, "LOGIN_SUCCESS")
```

- [ ] **Step 4: Add the SSO endpoints to `backend/api/auth.py`**

At the top of `backend/api/auth.py` (after Task 2's changes), the file reads:

```python
"""Login, logout and demo account management endpoints."""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, INACTIVE, ROLE_ADMIN, audit_auth, current_user, default_password,
    hash_password, identity_from_user, login as auth_login, logout as auth_logout,
    require_role, seed_demo_accounts, normalize_email,
)

router = APIRouter()


@router.get("/config")
def auth_config():
    return {"demo_enabled": os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true"}
```

Replace that entire block (imports through the end of the `/config` route Task 2 added — this step supersedes it with an equivalent route, so there must be only one `/config` definition afterward) with (adding `hashlib`, `secrets`, `msal`, `RedirectResponse`, and importing `issue_session`):

```python
"""Login, logout and demo account management endpoints."""
import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import msal

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, AUTH_COOKIE_SECURE, AUTH_COOKIE_SAMESITE, INACTIVE, ROLE_ADMIN, audit_auth,
    current_user, default_password, hash_password, identity_from_user, issue_session,
    login as auth_login, logout as auth_logout, require_role, seed_demo_accounts, normalize_email,
)

router = APIRouter()

SSO_STATE_COOKIE = "acrn_sso_state"
SSO_SCOPES = ["User.Read"]


def _sso_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=os.environ["ENTRA_CLIENT_ID"],
        client_credential=os.environ["ENTRA_CLIENT_SECRET"],
        authority=f"https://login.microsoftonline.com/{os.environ['ENTRA_TENANT_ID']}",
    )


def _sso_redirect_uri() -> str:
    return f"{os.environ['APP_BASE_URL'].rstrip('/')}/api/auth/sso/callback"


@router.get("/config")
def auth_config():
    return {"demo_enabled": os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true"}


@router.get("/sso/login")
def sso_login():
    state = secrets.token_urlsafe(24)
    auth_url = _sso_app().get_authorization_request_url(SSO_SCOPES, state=state, redirect_uri=_sso_redirect_uri())
    resp = RedirectResponse(auth_url)
    resp.set_cookie(SSO_STATE_COOKIE, state, httponly=True, secure=AUTH_COOKIE_SECURE, samesite=AUTH_COOKIE_SAMESITE, max_age=600, path="/")
    return resp


@router.get("/sso/callback")
def sso_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None,
                  acrn_sso_state: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    base = os.environ.get("APP_BASE_URL", "").rstrip("/")

    def redirect(path: str) -> RedirectResponse:
        r = RedirectResponse(f"{base}{path}")
        r.delete_cookie(SSO_STATE_COOKIE, path="/")
        return r

    if error or not code:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason=error or "No authorization code returned")
        db.commit()
        return redirect("/?sso_error=cancelled")

    if not state or not acrn_sso_state or state != acrn_sso_state:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason="State mismatch")
        db.commit()
        raise HTTPException(400, "Invalid SSO state")

    result = _sso_app().acquire_token_by_authorization_code(code, scopes=SSO_SCOPES, redirect_uri=_sso_redirect_uri())
    if "error" in result:
        audit_auth(db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason=result.get("error_description", "Token exchange failed"))
        db.commit()
        return redirect("/?sso_error=auth_failed")

    claims = result.get("id_token_claims", {})
    email = normalize_email(claims.get("preferred_username") or claims.get("email") or "")
    user = db.query(PortalUser).filter_by(email=email).first() if email else None
    if not user or user.status != ACTIVE:
        audit_auth(
            db, "SSO_LOGIN_FAILURE", "FAILURE", request=request, reason="Email not registered",
            details={"email_hash": hashlib.sha256(email.encode()).hexdigest()} if email else {},
        )
        db.commit()
        return redirect("/?sso_error=not_registered")

    resp = redirect("/")
    issue_session(db, user, resp, request, "SSO_LOGIN_SUCCESS")
    return resp
```

Note: this replaces the plain `/config` route added in Task 2 with the same route defined once here — the two edits target overlapping text, so apply this step's replacement in full rather than layering it on top of Task 2's block.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```
python -m pytest tests/test_sso_login.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Run the full existing backend suite to confirm no regression**

Run:
```
python -m pytest tests -v
```
Expected: all tests pass — in particular, existing password-login tests still pass since `issue_session` behaves identically to the old inline code.

- [ ] **Step 7: Commit**

```bash
git add backend/services/auth_service.py backend/api/auth.py backend/tests/test_sso_login.py
git commit -m "feat: add Microsoft Entra ID SSO login and callback endpoints"
```

---

### Task 4: Admin can create SSO-managed users and set `portal_role`/`study_scope`

**Files:**
- Modify: `backend/api/auth.py`
- Test: `backend/tests/test_user_provisioning.py`

**Interfaces:**
- Consumes: `PortalUser.portal_role`/`study_scope` (Task 1), `services.admin_security.ADMIN_ROLES`, `services.monitor_security.ROLES`.
- Produces: `POST /api/auth/users` (create), `POST /api/auth/users/{id}/portal-role`, `POST /api/auth/users/{id}/study-scope`. `public_user()`'s dict gains `portal_role` and `study_scope` keys — Task 7's frontend doesn't consume these directly, but this is the field an Admin UI would read/write going forward.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_user_provisioning.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models.auth import PortalUser
from services.auth_service import ACTIVE, hash_password

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def _login_as_admin():
    db = TestingSession()
    db.add(PortalUser(
        email="provisioning.admin@acrnhealth.com", display_name="Provisioning Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    r = client.post("/api/auth/login", json={"email": "provisioning.admin@acrnhealth.com", "password": "Whatever123!"})
    assert r.status_code == 200
    return {"acrn_demo_session": r.cookies["acrn_demo_session"]}


def test_admin_can_create_sso_managed_user_without_password():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={
            "email": "new.sso.monitor@acrnhealth.com", "display_name": "New SSO Monitor",
            "role": "MONITOR", "portal_role": "MONITOR_QC_REVIEWER", "study_scope": "PROTECT-Africa",
            "reason": "Provisioning for Microsoft SSO pilot",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "Monitor"
    assert body["portal_role"] == "MONITOR_QC_REVIEWER"
    assert body["study_scope"] == "PROTECT-Africa"

    db = TestingSession()
    row = db.query(PortalUser).filter_by(email="new.sso.monitor@acrnhealth.com").first()
    assert row.password_hash is None
    db.close()


def test_create_user_rejects_duplicate_email():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "provisioning.admin@acrnhealth.com", "display_name": "Dup", "role": "ADJUDICATOR", "reason": "Duplicate test"},
    )
    assert r.status_code == 409


def test_create_admin_requires_valid_portal_role():
    cookies = _login_as_admin()
    r = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "bad.role@acrnhealth.com", "display_name": "Bad Role", "role": "ADMIN", "portal_role": "NOT_A_REAL_ROLE", "reason": "Invalid role test"},
    )
    assert r.status_code == 422


def test_set_study_scope_updates_existing_user():
    cookies = _login_as_admin()
    create = client.post(
        "/api/auth/users", cookies=cookies,
        json={"email": "scope.test@acrnhealth.com", "display_name": "Scope Test", "role": "MONITOR", "portal_role": "QA_REVIEWER", "reason": "Scope test setup"},
    )
    user_id = create.json()["id"]
    r = client.post(f"/api/auth/users/{user_id}/study-scope", cookies=cookies, json={"study_scope": "LOPE-Nigeria", "reason": "Narrowing scope"})
    assert r.status_code == 200
    assert r.json()["study_scope"] == "LOPE-Nigeria"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
python -m pytest tests/test_user_provisioning.py -v
```
Expected: FAIL — 404s on `/api/auth/users` POST and `/api/auth/users/{id}/study-scope` (routes don't exist yet).

- [ ] **Step 3: Update `public_user()` and add the new endpoints**

In `backend/api/auth.py`, the current `public_user()` function reads:

```python
def public_user(user: PortalUser) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name,
        "role": user.role.title(),
        "roleCode": user.role,
        "portal": {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator"}[user.role],
        "status": user.status,
        "is_demo_account": user.is_demo_account,
        "demo": user.is_demo_account,
        "must_change_password": user.must_change_password,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
```

Replace it with:

```python
def public_user(user: PortalUser) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name,
        "role": user.role.title(),
        "roleCode": user.role,
        "portal_role": user.portal_role,
        "study_scope": user.study_scope,
        "portal": {"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator"}[user.role],
        "status": user.status,
        "is_demo_account": user.is_demo_account,
        "demo": user.is_demo_account,
        "must_change_password": user.must_change_password,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
```

Then, in the same file, immediately after the `class RoleRequest(ReasonRequest):` block (which reads):

```python
class RoleRequest(ReasonRequest):
    role: str
```

add two new request models directly below it:

```python
class RoleRequest(ReasonRequest):
    role: str


class CreateUserRequest(ReasonRequest):
    email: str
    display_name: str
    role: str
    portal_role: Optional[str] = None
    study_scope: str = "*"


class PortalRoleRequest(ReasonRequest):
    portal_role: Optional[str] = None


class StudyScopeRequest(ReasonRequest):
    study_scope: str
```

Then, near the top of the file, extend the import line that currently reads:

```python
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, AUTH_COOKIE_SECURE, AUTH_COOKIE_SAMESITE, INACTIVE, ROLE_ADMIN, audit_auth,
    current_user, default_password, hash_password, identity_from_user, issue_session,
    login as auth_login, logout as auth_logout, require_role, seed_demo_accounts, normalize_email,
)
```

by adding two new imports right after it:

```python
from services.auth_service import (
    ACTIVE, AUTH_COOKIE, AUTH_COOKIE_SECURE, AUTH_COOKIE_SAMESITE, INACTIVE, ROLE_ADMIN, audit_auth,
    current_user, default_password, hash_password, identity_from_user, issue_session,
    login as auth_login, logout as auth_logout, require_role, seed_demo_accounts, normalize_email,
)
from services.admin_security import ADMIN_ROLES
from services.monitor_security import ROLES as MONITOR_ROLES
```

Finally, add the three new endpoints right after the existing `set_role` endpoint. The file currently has this block:

```python
@router.post("/users/{user_id}/role")
def set_role(user_id: str, req: RoleRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
             db: Session = Depends(get_db)):
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR"}:
        raise HTTPException(422, "Unsupported role")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    previous = row.role
    row.role = role
    audit_auth(db, "ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason, details={"previous_role": previous, "role": role})
    db.commit()
    return public_user(row)
```

Insert the new endpoints directly after it (before the `@router.get("/audit")` block):

```python
@router.post("/users/{user_id}/role")
def set_role(user_id: str, req: RoleRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
             db: Session = Depends(get_db)):
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR"}:
        raise HTTPException(422, "Unsupported role")
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    previous = row.role
    row.role = role
    audit_auth(db, "ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason, details={"previous_role": previous, "role": role})
    db.commit()
    return public_user(row)


def _validate_portal_role(role: str, portal_role: Optional[str]):
    if role == "ADMIN" and portal_role not in ADMIN_ROLES:
        raise HTTPException(422, f"portal_role must be one of: {', '.join(sorted(ADMIN_ROLES))}")
    if role == "MONITOR" and portal_role not in MONITOR_ROLES:
        raise HTTPException(422, f"portal_role must be one of: {', '.join(sorted(MONITOR_ROLES))}")


@router.post("/users", status_code=201)
def create_user(req: CreateUserRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                 db: Session = Depends(get_db)):
    role = req.role.upper()
    if role not in {"ADMIN", "MONITOR", "ADJUDICATOR"}:
        raise HTTPException(422, "Unsupported role")
    normalized = normalize_email(req.email)
    if db.query(PortalUser).filter_by(email=normalized).first():
        raise HTTPException(409, "A user with this email already exists")
    portal_role = (req.portal_role or "").upper() or None
    _validate_portal_role(role, portal_role)
    row = PortalUser(
        email=normalized,
        display_name=req.display_name,
        password_hash=None,
        role=role,
        portal_role=portal_role,
        study_scope=req.study_scope or "*",
        status=ACTIVE,
        is_demo_account=False,
    )
    db.add(row)
    audit_auth(db, "USER_CREATED", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"role": role, "portal_role": portal_role})
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/portal-role")
def set_portal_role(user_id: str, req: PortalRoleRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                     db: Session = Depends(get_db)):
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    portal_role = (req.portal_role or "").upper() or None
    _validate_portal_role(row.role, portal_role)
    previous = row.portal_role
    row.portal_role = portal_role
    audit_auth(db, "PORTAL_ROLE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"previous_portal_role": previous, "portal_role": portal_role})
    db.commit()
    return public_user(row)


@router.post("/users/{user_id}/study-scope")
def set_study_scope(user_id: str, req: StudyScopeRequest, request: Request, admin: PortalUser = Depends(require_role(ROLE_ADMIN)),
                     db: Session = Depends(get_db)):
    row = db.get(PortalUser, user_id)
    if not row:
        raise HTTPException(404, "User not found")
    previous = row.study_scope
    row.study_scope = req.study_scope
    audit_auth(db, "STUDY_SCOPE_CHANGE", "SUCCESS", actor=admin, affected=row, request=request, reason=req.reason,
               details={"previous_study_scope": previous, "study_scope": req.study_scope})
    db.commit()
    return public_user(row)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m pytest tests/test_user_provisioning.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Run the full existing backend suite to confirm no regression**

Run:
```
python -m pytest tests -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/api/auth.py backend/tests/test_user_provisioning.py
git commit -m "feat: let Admins pre-provision SSO-managed users with portal_role and study_scope"
```

---

### Task 5: Close the Admin Portal header-trust gap

**Files:**
- Modify: `backend/services/admin_security.py`
- Modify: `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: `PortalUser.portal_role`/`study_scope` (Task 1).
- Produces: `get_identity()` now derives `Identity.role`/`Identity.studies` from the session-backed `PortalUser` whenever a valid session exists; `X-Demo-*` headers are only consulted when `ENABLE_DEMO_ACCOUNTS=true` and no valid session is present.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_admin.py`, the file currently starts with:

```python
"""Admin Portal authorization, scope, versioning, blinding, audit and demo tests."""
from datetime import datetime, timedelta
import os, sys
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import Base, get_db
from main import app
from models.admin import AdminUser, ControlledVersion, AdminAuditEvent
from services.admin_security import Identity, validate_mapping, validate_workflow_definition, risk_warnings

engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

def override_db():
    db=TestingSession()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=override_db
client=TestClient(app)
CLIN={"X-Demo-User":"clinical.ops.demo@acrnhealth.com","X-Demo-Role":"CLINICAL_OPS_ADMIN","X-Study-Scope":"PROTECT-Africa,LOPE-Nigeria"}
TECH={"X-Demo-User":"tech.admin.demo@acrnhealth.com","X-Demo-Role":"TECHNICAL_ADMIN","X-Study-Scope":"*"}
```

Replace it with (adding the `PortalUser`/`hash_password` imports and forcing `ENABLE_DEMO_ACCOUNTS=true` for this module, since every existing test in this file authenticates via the header fallback, which this task restricts to demo mode only):

```python
"""Admin Portal authorization, scope, versioning, blinding, audit and demo tests."""
from datetime import datetime, timedelta
import os, sys
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["ENABLE_DEMO_ACCOUNTS"] = "true"
from database import Base, get_db
from main import app
from models.admin import AdminUser, ControlledVersion, AdminAuditEvent
from models.auth import PortalUser
from services.admin_security import Identity, validate_mapping, validate_workflow_definition, risk_warnings
from services.auth_service import ACTIVE, hash_password

engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

def override_db():
    db=TestingSession()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=override_db
client=TestClient(app)
CLIN={"X-Demo-User":"clinical.ops.demo@acrnhealth.com","X-Demo-Role":"CLINICAL_OPS_ADMIN","X-Study-Scope":"PROTECT-Africa,LOPE-Nigeria"}
TECH={"X-Demo-User":"tech.admin.demo@acrnhealth.com","X-Demo-Role":"TECHNICAL_ADMIN","X-Study-Scope":"*"}
```

Then add these three new test functions at the end of the file (after the existing `test_audit_events_immutable` test):

```python
def test_admin_headers_rejected_when_demo_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    r = client.get("/api/admin/dashboard", headers=CLIN)
    assert r.status_code == 401


def test_admin_session_grants_access_using_portal_role(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="sso.tech.admin@acrnhealth.com", display_name="SSO Tech Admin",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role="TECHNICAL_ADMIN", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.tech.admin@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/admin/dashboard", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200


def test_admin_session_without_portal_role_denied(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role@acrnhealth.com", display_name="No Portal Role",
        password_hash=hash_password("Whatever123!"), role="ADMIN", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/admin/dashboard", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to verify the three new tests fail**

Run:
```
python -m pytest tests/test_admin.py -v
```
Expected: the pre-existing tests pass (module now sets `ENABLE_DEMO_ACCOUNTS=true`), but the three new tests FAIL — `get_identity` doesn't yet check `ENABLE_DEMO_ACCOUNTS` or read `portal_role` from the session.

- [ ] **Step 3: Rewrite `get_identity`**

In `backend/services/admin_security.py`, the imports at the top currently read:

```python
"""Replaceable identity adapter and server-side Admin Portal authorization."""
import hashlib, json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, Depends, Request, Cookie
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import event
from models.admin import AdminAuditEvent
from models.auth import PortalUser
```

Replace with (adding `os`):

```python
"""Replaceable identity adapter and server-side Admin Portal authorization."""
import hashlib, json, os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, Depends, Request, Cookie
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import event
from models.admin import AdminAuditEvent
from models.auth import PortalUser
```

Then, the current `get_identity` function reads:

```python
def get_identity(request: Request, acrn_demo_session: Optional[str] = Cookie(None), db: Session = Depends(get_db), x_demo_user: Optional[str] = Header(None), x_demo_role: Optional[str] = Header(None), x_study_scope: Optional[str] = Header(None)):
    """Session adapter with legacy demo-header fallback for older local tests."""
    try:
        token = acrn_demo_session
        if token:
            from services.auth_service import _hash_token
            from models.auth import AuthSession
            session = db.query(AuthSession).filter_by(token_hash=_hash_token(token), revoked_at=None).first()
            if session and session.expires_at > datetime.utcnow():
                user = db.get(PortalUser, session.user_id)
                if user and user.status == "ACTIVE" and user.role in ADMIN_ROLES:
                    return Identity(user.email, user.role, tuple(filter(None, (x_study_scope or "*").split(","))))
                if user and user.status == "ACTIVE":
                    raise HTTPException(403, "Admin Portal access denied for this role.")
    except HTTPException:
        raise
    except Exception:
        pass
    if not x_demo_user or not x_demo_role:
        raise HTTPException(401, "Authentication required.")
    role = x_demo_role.upper()
    if role not in ADMIN_ROLES:
        raise HTTPException(403, "Admin Portal access denied for this role.")
    return Identity(x_demo_user, role, tuple(filter(None, (x_study_scope or "").split(","))))
```

Replace it with:

```python
def get_identity(request: Request, acrn_demo_session: Optional[str] = Cookie(None), db: Session = Depends(get_db), x_demo_user: Optional[str] = Header(None), x_demo_role: Optional[str] = Header(None), x_study_scope: Optional[str] = Header(None)):
    """Resolves identity from the session-backed PortalUser. X-Demo-* headers are only
    trusted as a fallback when ENABLE_DEMO_ACCOUNTS=true and no valid session is present."""
    if acrn_demo_session:
        from services.auth_service import _hash_token
        from models.auth import AuthSession
        session = db.query(AuthSession).filter_by(token_hash=_hash_token(acrn_demo_session), revoked_at=None).first()
        if session and session.expires_at > datetime.utcnow():
            user = db.get(PortalUser, session.user_id)
            if user and user.status == "ACTIVE":
                if user.role != "ADMIN" or user.portal_role not in ADMIN_ROLES:
                    raise HTTPException(403, "Admin Portal access denied for this role.")
                studies = tuple(filter(None, (user.study_scope or "*").split(",")))
                return Identity(user.email, user.portal_role, studies, auth_source="SSO" if user.password_hash is None else "SESSION")

    if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() != "true":
        raise HTTPException(401, "Authentication required.")

    if not x_demo_user or not x_demo_role:
        raise HTTPException(401, "Authentication required.")
    role = x_demo_role.upper()
    if role not in ADMIN_ROLES:
        raise HTTPException(403, "Admin Portal access denied for this role.")
    return Identity(x_demo_user, role, tuple(filter(None, (x_study_scope or "").split(","))), auth_source="DEMO")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m pytest tests/test_admin.py -v
```
Expected: all tests pass, including the three new ones.

- [ ] **Step 5: Run the full existing backend suite to confirm no regression**

Run:
```
python -m pytest tests -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/admin_security.py backend/tests/test_admin.py
git commit -m "fix: derive Admin Portal identity from the session, not client-supplied headers"
```

---

### Task 6: Close the Monitor Portal header-trust gap

**Files:**
- Modify: `backend/services/monitor_security.py`
- Modify: `backend/tests/test_monitor.py`

**Interfaces:**
- Consumes: `PortalUser.portal_role`/`study_scope` (Task 1).
- Produces: `identity()` now derives `MonitorIdentity.role`/`studies` from the session-backed `PortalUser` whenever a valid session exists; `X-Demo-*` headers are only consulted when `ENABLE_DEMO_ACCOUNTS=true` and no valid session is present.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_monitor.py`, the file currently starts with:

```python
import os,sys,pytest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from services.monitor_security import scan_blinding,validate_import,qc_gate,assignment_gate,release_gate
from services.workflow_policy import check_reviewer_isolation,check_committee_quorum,evaluate_concordance
```

Replace it with (this file has no `TestClient`/DB setup today — this task adds one, since the new tests need to hit a real endpoint through the app):

```python
import os,sys,pytest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from services.monitor_security import scan_blinding,validate_import,qc_gate,assignment_gate,release_gate
from services.workflow_policy import check_reviewer_isolation,check_committee_quorum,evaluate_concordance

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _client():
    from database import Base, get_db
    from main import app
    Base.metadata.create_all(engine)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)
```

Then add these new test functions at the end of the file:

```python
def test_monitor_headers_rejected_when_demo_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    client = _client()
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 401


def test_monitor_headers_accepted_when_demo_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "true")
    client = _client()
    r = client.get("/api/monitor/me", headers={"X-Demo-User": "monitor.demo@acrnhealth.com", "X-Demo-Role": "MONITOR_QC_REVIEWER"})
    assert r.status_code == 200


def test_monitor_session_grants_access_using_portal_role(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    client = _client()
    db = TestingSession()
    db.add(PortalUser(
        email="sso.monitor@acrnhealth.com", display_name="SSO Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role="MONITOR_QC_REVIEWER", status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "sso.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 200
    assert r.json()["role"] == "MONITOR_QC_REVIEWER"


def test_monitor_session_without_portal_role_denied(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNTS", "false")
    from models.auth import PortalUser
    from services.auth_service import ACTIVE, hash_password
    client = _client()
    db = TestingSession()
    db.add(PortalUser(
        email="no.portal.role.monitor@acrnhealth.com", display_name="No Portal Role Monitor",
        password_hash=hash_password("Whatever123!"), role="MONITOR", portal_role=None, status=ACTIVE,
    ))
    db.commit()
    db.close()
    login = client.post("/api/auth/login", json={"email": "no.portal.role.monitor@acrnhealth.com", "password": "Whatever123!"})
    assert login.status_code == 200
    r = client.get("/api/monitor/me", cookies={"acrn_demo_session": login.cookies["acrn_demo_session"]})
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run:
```
python -m pytest tests/test_monitor.py -v
```
Expected: pre-existing pure-function tests still pass; the four new tests FAIL (`identity()` has no session support or demo-mode gate yet).

- [ ] **Step 3: Rewrite `identity()`**

`backend/services/monitor_security.py` currently reads in full:

```python
import hashlib,json
from dataclasses import dataclass
from datetime import datetime,timezone
from fastapi import Header,HTTPException,Depends
from models.monitor import MonitorAuditEvent
ROLES={"ADJUDICATION_COORDINATOR","MONITOR_QC_REVIEWER","QA_REVIEWER","RELEASE_OPERATOR"}
PROHIBITED=("sflt-1","sflt1","plgf","seng","biomarker","poc result","treatment allocation","randomisation","randomization")
@dataclass(frozen=True)
class MonitorIdentity: upn:str; role:str; studies:tuple[str,...]
def identity(x_demo_user:str|None=Header(None),x_demo_role:str|None=Header(None),x_study_scope:str|None=Header(None)):
    if not x_demo_user or not x_demo_role: raise HTTPException(401,"Authentication required")
    if x_demo_role.upper() not in ROLES: raise HTTPException(403,"Monitor Portal access denied")
    return MonitorIdentity(x_demo_user,x_demo_role.upper(),tuple(filter(None,(x_study_scope or "").split(","))))
```

Replace the imports and `identity()` function (leaving everything from `def scope(...)` onward unchanged) with:

```python
import hashlib,json,os
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Optional
from fastapi import Cookie,Header,HTTPException,Depends
from sqlalchemy.orm import Session
from database import get_db
from models.auth import PortalUser
from models.monitor import MonitorAuditEvent
ROLES={"ADJUDICATION_COORDINATOR","MONITOR_QC_REVIEWER","QA_REVIEWER","RELEASE_OPERATOR"}
PROHIBITED=("sflt-1","sflt1","plgf","seng","biomarker","poc result","treatment allocation","randomisation","randomization")
@dataclass(frozen=True)
class MonitorIdentity: upn:str; role:str; studies:tuple[str,...]
def identity(acrn_demo_session:Optional[str]=Cookie(None),db:Session=Depends(get_db),x_demo_user:Optional[str]=Header(None),x_demo_role:Optional[str]=Header(None),x_study_scope:Optional[str]=Header(None)):
    if acrn_demo_session:
        from services.auth_service import _hash_token
        from models.auth import AuthSession
        session=db.query(AuthSession).filter_by(token_hash=_hash_token(acrn_demo_session),revoked_at=None).first()
        if session and session.expires_at>datetime.utcnow():
            user=db.get(PortalUser,session.user_id)
            if user and user.status=="ACTIVE":
                if user.role!="MONITOR" or user.portal_role not in ROLES: raise HTTPException(403,"Monitor Portal access denied")
                studies=tuple(filter(None,(user.study_scope or "*").split(",")))
                return MonitorIdentity(user.email,user.portal_role,studies)
    if os.getenv("ENABLE_DEMO_ACCOUNTS","false").lower()!="true": raise HTTPException(401,"Authentication required")
    if not x_demo_user or not x_demo_role: raise HTTPException(401,"Authentication required")
    if x_demo_role.upper() not in ROLES: raise HTTPException(403,"Monitor Portal access denied")
    return MonitorIdentity(x_demo_user,x_demo_role.upper(),tuple(filter(None,(x_study_scope or "").split(","))))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m pytest tests/test_monitor.py -v
```
Expected: all tests pass, including the four new ones.

- [ ] **Step 5: Run the full existing backend suite to confirm no regression**

Run:
```
python -m pytest tests -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/monitor_security.py backend/tests/test_monitor.py
git commit -m "fix: derive Monitor Portal identity from the session, not client-supplied headers"
```

---

### Task 7: Frontend login page — "Sign in with Microsoft"

**Files:**
- Modify: `src/services/authApi.js`
- Modify: `src/components/LoginPage.jsx`

**Interfaces:**
- Consumes: `GET /api/auth/config` (Task 2), `GET /api/auth/sso/login` (Task 3).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the config fetch and SSO login URL to `authApi.js`**

`src/services/authApi.js` currently reads:

```js
const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (!res.ok) {
    let detail = 'Request failed';
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.message || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export const login = (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
export const logout = () => request('/auth/logout', { method: 'POST', body: '{}' });
export const me = () => request('/auth/me');
export const listUsers = (params = {}) => request(`/auth/users?${new URLSearchParams(params)}`);
export const setUserStatus = (id, status, reason) => request(`/auth/users/${id}/status`, { method: 'POST', body: JSON.stringify({ status, reason }) });
export const unlockUser = (id, reason) => request(`/auth/users/${id}/unlock`, { method: 'POST', body: JSON.stringify({ reason }) });
export const resetDemoPassword = (id, reason) => request(`/auth/users/${id}/reset-password`, { method: 'POST', body: JSON.stringify({ reason }) });
export const setUserRole = (id, role, reason) => request(`/auth/users/${id}/role`, { method: 'POST', body: JSON.stringify({ role, reason }) });
```

Add two new exports at the end of the file:

```js
export const getAuthConfig = () => request('/auth/config');
export const SSO_LOGIN_URL = `${BASE}/auth/sso/login`;
```

- [ ] **Step 2: Update `LoginPage.jsx`**

The current imports and component opening read:

```jsx
import React, { useState } from 'react';
import { login } from '../services/authApi';

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('admin@acrnhealth.com');
  const [password, setPassword] = useState('ACRN@2026');
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);
```

Replace with:

```jsx
import React, { useEffect, useState } from 'react';
import { login, getAuthConfig, SSO_LOGIN_URL } from '../services/authApi';

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('admin@acrnhealth.com');
  const [password, setPassword] = useState('ACRN@2026');
  const [errorMsg, setErrorMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(false);

  useEffect(() => {
    getAuthConfig().then((cfg) => setDemoEnabled(!!cfg.demo_enabled)).catch(() => setDemoEnabled(false));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ssoError = params.get('sso_error');
    if (ssoError) {
      const messages = {
        not_registered: "Your account isn't registered. Contact your administrator to be added.",
        cancelled: 'Microsoft sign-in was cancelled.',
        auth_failed: 'Microsoft sign-in failed. Please try again.',
      };
      setErrorMsg(messages[ssoError] || 'Microsoft sign-in failed. Please try again.');
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);
```

Then, the form section currently reads:

```jsx
          <form onSubmit={handleSubmit}>
            <div style={{ background: '#fff7ed', border: '1px solid #fdba74', borderLeft: '3px solid #F07E26', padding: '12px 14px', borderRadius: '6px', fontSize: '12px', marginBottom: '18px', color: '#7c2d12' }}>
              <div style={{ fontWeight: 700, marginBottom: '6px' }}>Select Demo Account / Role:</div>
```

Replace the opening `<form onSubmit={handleSubmit}>` line with a "Sign in with Microsoft" button placed before the form, and wrap the whole form in the `demoEnabled` condition:

```jsx
          <button
            type="button"
            onClick={() => { window.location.href = SSO_LOGIN_URL; }}
            style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700, color: '#ffffff', backgroundColor: '#0f172a', border: 'none', borderRadius: '6px', cursor: 'pointer', marginBottom: demoEnabled ? '20px' : '0' }}
          >
            Sign in with Microsoft
          </button>

          {errorMsg && (
            <div style={{ background: '#fef2f2', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginTop: '18px' }}>
              {errorMsg}
            </div>
          )}

          {demoEnabled && (
          <form onSubmit={handleSubmit} style={{ marginTop: '20px' }}>
            <div style={{ background: '#fff7ed', border: '1px solid #fdba74', borderLeft: '3px solid #F07E26', padding: '12px 14px', borderRadius: '6px', fontSize: '12px', marginBottom: '18px', color: '#7c2d12' }}>
              <div style={{ fontWeight: 700, marginBottom: '6px' }}>Select Demo Account / Role:</div>
```

The existing `{errorMsg && (...)}` block further down inside the form (which duplicates what was just moved above the form) currently reads:

```jsx
            {errorMsg && (
              <div style={{ background: '#fef2f2', color: '#dc2626', padding: '10px 14px', borderRadius: '6px', fontSize: '13px', marginBottom: '18px' }}>
                {errorMsg}
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
```

Remove that duplicated block, leaving just:

```jsx
            <div style={{ marginBottom: '20px' }}>
```

Finally, the form's closing tag and the "Request access" section currently read:

```jsx
            <button type="submit" disabled={busy} style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700, color: '#ffffff', backgroundColor: busy ? '#94a3b8' : '#ea580c', border: 'none', borderRadius: '6px', cursor: busy ? 'wait' : 'pointer' }}>
              {busy ? 'Checking account...' : 'Access Portal'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '20px' }}>
```

Close the new conditional right after the form's closing tag:

```jsx
            <button type="submit" disabled={busy} style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700, color: '#ffffff', backgroundColor: busy ? '#94a3b8' : '#ea580c', border: 'none', borderRadius: '6px', cursor: busy ? 'wait' : 'pointer' }}>
              {busy ? 'Checking account...' : 'Access Portal'}
            </button>
          </form>
          )}

          <div style={{ textAlign: 'center', marginTop: '20px' }}>
```

- [ ] **Step 3: Verify the frontend builds**

Run (from the repo root):
```
npm run build
```
Expected: build succeeds with no errors.

- [ ] **Step 4: Manual verification**

Run the dev server (`npm run dev` + backend running with `ENABLE_DEMO_ACCOUNTS=true`) and confirm in a browser: the "Sign in with Microsoft" button is visible, the demo account box and form are visible below it (since demo is enabled), and clicking "Sign in with Microsoft" navigates to `/api/auth/sso/login` (it will fail past that point without a real Entra app registration configured — that's expected at this stage). Then confirm that with the backend started with `ENABLE_DEMO_ACCOUNTS=false`, only the "Sign in with Microsoft" button appears and the demo form is hidden.

- [ ] **Step 5: Commit**

```bash
git add src/services/authApi.js src/components/LoginPage.jsx
git commit -m "feat: add Sign in with Microsoft to the login page, gate demo login behind ENABLE_DEMO_ACCOUNTS"
```

---

### Task 8: Configuration templates, Azure setup guide, README

**Files:**
- Modify: `.env.dev.example`
- Modify: `.env.prod.example`
- Create: `docs/entra-sso-setup.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `APP_BASE_URL` (Task 3).
- Produces: the final documentation deliverables. Nothing downstream depends on them.

- [ ] **Step 1: Add the new env vars to `.env.dev.example`**

The file currently ends with:

```
RT_PSEUDONYM_SECRET=change-me-dev-pseudonym-secret
RT_IDENTITY_ENCRYPTION_KEY=
```

Append:

```

# Microsoft Entra ID SSO (see docs/entra-sso-setup.md for how to obtain these)
ENTRA_TENANT_ID=
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
APP_BASE_URL=https://adjudication-dev.acrncloud.com
```

- [ ] **Step 2: Add the new env vars to `.env.prod.example`**

The file currently ends with:

```
RT_PSEUDONYM_SECRET=
RT_IDENTITY_ENCRYPTION_KEY=
```

Append:

```

# Microsoft Entra ID SSO (see docs/entra-sso-setup.md for how to obtain these)
ENTRA_TENANT_ID=
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
APP_BASE_URL=https://adjudication.acrncloud.com
```

- [ ] **Step 3: Write `docs/entra-sso-setup.md`**

Create `docs/entra-sso-setup.md`:

```markdown
# Microsoft Entra ID SSO Setup

Do this once per environment (Dev and Prod each get their own App Registration, matching how this project already keeps dev/prod fully isolated).

**Callback URLs to register:**
- Prod: `https://adjudication.acrncloud.com/api/auth/sso/callback`
- Dev: `https://adjudication-dev.acrncloud.com/api/auth/sso/callback`

## Steps in the Azure Portal (repeat per environment)

1. Go to [portal.azure.com](https://portal.azure.com) -> **Microsoft Entra ID** -> **App registrations** -> **+ New registration**.
2. Name it something identifiable, e.g. "ACRN Adjudication Platform (Dev)" / "(Prod)".
3. Supported account types: **Accounts in this organizational directory only (Single tenant)**.
4. Redirect URI - platform **Web**, value = the callback URL above for that environment.
5. Click **Register**.
6. From the **Overview** page, record:
   - **Application (client) ID** -> `ENTRA_CLIENT_ID`
   - **Directory (tenant) ID** -> `ENTRA_TENANT_ID`
7. **Certificates & secrets** -> **+ New client secret** -> set an expiry -> **Add** -> copy the secret's **Value** immediately (shown once) -> `ENTRA_CLIENT_SECRET`. Type this directly into the server's `.env.dev`/`.env.prod` file — never commit it.
8. **API permissions**: the default **Microsoft Graph -> User.Read** (delegated) permission is already sufficient — no admin consent required.
9. Leave **Authentication -> Front-channel logout URL** blank.
10. No changes are needed under "Implicit grant and hybrid flows" for this flow.

## After registration

On the server, fill in `.env.dev` (or `.env.prod`):

```
ENTRA_TENANT_ID=<Directory (tenant) ID from step 6>
ENTRA_CLIENT_ID=<Application (client) ID from step 6>
ENTRA_CLIENT_SECRET=<secret value from step 7>
APP_BASE_URL=https://adjudication-dev.acrncloud.com   # or the prod URL on the prod server
```

Then redeploy (`./scripts/deploy-dev.sh` or `./scripts/deploy-prod.sh`).

**Before the first deploy after this feature ships**, run the schema migration against that server's Postgres database (this does not happen automatically):

```
psql "$DATABASE_URL" -f backend/migrations/versions/20260812_05_sso_login.sql
```

## Provisioning a user

Microsoft SSO only lets in users who already have a `PortalUser` record. An Admin creates one via the Admin portal's user management (`POST /api/auth/users`), specifying:
- `email` — must exactly match the user's Microsoft work account email.
- `role` — `ADMIN`, `MONITOR`, or `ADJUDICATOR`.
- `portal_role` — required for `ADMIN`/`MONITOR` accounts (e.g. `TECHNICAL_ADMIN`, `MONITOR_QC_REVIEWER`); leave unset for `ADJUDICATOR`.
- `study_scope` — comma-separated study codes, or `*` for all studies (default).

No password is set — the account authenticates purely through Microsoft.
```

- [ ] **Step 4: Update `README.md`**

Find the environment variables table row for `SECRET_KEY` (added in the earlier Docker deployment work) and add four new rows directly after the table's last row. Locate the end of that table (the `AUTH_COOKIE_SECURE` row or whichever is currently last) and append:

```
| `ENTRA_TENANT_ID` | yes on real dev/prod | Microsoft Entra ID tenant ID. See [docs/entra-sso-setup.md](docs/entra-sso-setup.md). |
| `ENTRA_CLIENT_ID` | yes on real dev/prod | Entra App Registration client ID. |
| `ENTRA_CLIENT_SECRET` | yes on real dev/prod | Entra App Registration client secret. |
| `APP_BASE_URL` | yes on real dev/prod | This environment's public HTTPS URL, used to build the SSO redirect URI. |
```

Then find the "Local development" or login-related section describing demo accounts, and add a short paragraph directly after it:

```markdown
### Microsoft SSO (dev/prod)

On the real ACRN dev/prod servers (`ENABLE_DEMO_ACCOUNTS=false`), only Microsoft Entra ID sign-in is accepted — the demo email/password form is hidden. See [docs/entra-sso-setup.md](docs/entra-sso-setup.md) for setting up the Azure App Registration and provisioning users.
```

- [ ] **Step 5: Commit**

```bash
git add .env.dev.example .env.prod.example docs/entra-sso-setup.md README.md
git commit -m "docs: add Microsoft Entra ID setup guide and env var documentation"
```

---

## Final verification (after all tasks)

- [ ] Run the full backend suite one more time from a clean state:
```bash
cd backend
python -m pytest tests -v
```
Expected: all tests pass, including every new SSO/portal-role/study-scope test added across Tasks 1-6.

- [ ] Run the frontend build once more:
```bash
npm run build
```
Expected: succeeds with no errors.

- [ ] Confirm the migration note is visible: re-read `docs/entra-sso-setup.md` and the Global Constraints section of this plan — before this feature can work on the real dev/prod servers, `backend/migrations/versions/20260812_05_sso_login.sql` must be run manually against each server's Postgres database, and an Azure App Registration must exist per the setup guide with `ENTRA_*`/`APP_BASE_URL` filled into that server's `.env.dev`/`.env.prod`.
