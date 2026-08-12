# Docker Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerize the ACRN Adjudication Platform into one Docker image (FastAPI + built React SPA), add one-command dev/prod/local deploy scripts, wire up external SSL-required Postgres, and rewrite the README.

**Architecture:** A multi-stage root `Dockerfile` builds the Vite frontend in a Node stage and copies the output into a Python 3.12 runtime stage that runs the existing FastAPI app (`backend/main.py` already serves `dist/` as the SPA). `docker-compose.yml` defines a single `app` service; `docker-compose.dev.yml` / `docker-compose.prod.yml` layer in environment-specific config pointing at ACRN's external Postgres instances; `docker-compose.localdb.yml` is an opt-in override that adds a throwaway Postgres container for offline development. Shell + PowerShell scripts wrap the `docker compose` invocations into one command each.

**Tech Stack:** Docker, Docker Compose v2, Node 20 (build-only), Python 3.12, FastAPI, PostgreSQL (external, SSL).

## Global Constraints

- No app feature/UI changes — this is deployment infrastructure only.
- Exactly one application code change permitted: `backend/database.py` gains `DB_SSL_MODE` support.
- No TLS/reverse-proxy container — the ACRN server edge already terminates HTTPS; the app container exposes plain HTTP.
- No DB container in the dev/prod deploy path — Postgres is external and SSL-required (`DB_SSL_MODE=require`). The bundled Postgres container is opt-in and local-only.
- No Alembic — the app keeps its existing `Base.metadata.create_all()` startup behavior.
- Host port defaults to `8005` on both servers (dev and prod are separate machines), overridable via `APP_PORT`.
- Real secrets (`.env.dev`, `.env.prod`, `.env.local`) are never committed; only `.env.*.example` templates are tracked.
- Design reference: `docs/superpowers/specs/2026-08-12-docker-deployment-design.md`.

---

### Task 1: `backend/database.py` — DB_SSL_MODE support

**Files:**
- Modify: `backend/database.py`
- Test: `backend/tests/test_database_ssl_mode.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `database._build_postgres_connect_args() -> dict` — used internally by `_create_engine_with_fallback()`. Later tasks (Dockerfile's `pytest` run) rely on this test file existing under `backend/tests/`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_database_ssl_mode.py`:

```python
import os
import sys


def _ensure_backend_on_path():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def test_db_ssl_mode_included_in_connect_args(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.setenv("DB_SSL_MODE", "require")
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_connect_args() == {"sslmode": "require"}
    sys.modules.pop("database", None)


def test_db_ssl_mode_omitted_when_unset(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.delenv("DB_SSL_MODE", raising=False)
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_connect_args() == {}
    sys.modules.pop("database", None)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, with a Python 3.12 environment that has `backend/requirements.txt` installed):
```
python -m pytest tests/test_database_ssl_mode.py -v
```
Expected: FAIL with `AttributeError: module 'database' has no attribute '_build_postgres_connect_args'`.

- [ ] **Step 3: Implement `_build_postgres_connect_args()` and use it**

In `backend/database.py`, the current block reads:

```python
_POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://acrn_user:acrn_dev_password@localhost:5432/acrn_adjudication"
)
_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "acrn_demo.db")
_SQLITE_URL = f"sqlite:///{_SQLITE_PATH}"

DB_OFFLINE = False

def _create_engine_with_fallback():
    global DB_OFFLINE
    try:
        eng = create_engine(_POSTGRES_URL, pool_pre_ping=True, connect_args={})
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connection established.")
        return eng, False
```

Replace it with:

```python
_POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://acrn_user:acrn_dev_password@localhost:5432/acrn_adjudication"
)
_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "acrn_demo.db")
_SQLITE_URL = f"sqlite:///{_SQLITE_PATH}"
_DB_SSL_MODE = os.getenv("DB_SSL_MODE")

DB_OFFLINE = False


def _build_postgres_connect_args():
    """Optional psycopg2 sslmode, e.g. DB_SSL_MODE=require for an external managed Postgres."""
    return {"sslmode": _DB_SSL_MODE} if _DB_SSL_MODE else {}


def _create_engine_with_fallback():
    global DB_OFFLINE
    try:
        eng = create_engine(_POSTGRES_URL, pool_pre_ping=True, connect_args=_build_postgres_connect_args())
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connection established.")
        return eng, False
```

Use the Edit tool with the block above as `old_string` and the replacement as `new_string` — the rest of the file (the `except` branch, `SessionLocal`, `get_db`) is unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run:
```
python -m pytest tests/test_database_ssl_mode.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Run the full existing backend suite to confirm no regression**

Run (from `backend/`):
```
python -m pytest tests -v
```
Expected: all tests pass (existing suite is unaffected since `DB_SSL_MODE` is unset by default, so `_build_postgres_connect_args()` returns `{}` — identical to the old hardcoded `{}`).

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/tests/test_database_ssl_mode.py
git commit -m "feat: support DB_SSL_MODE for external Postgres connections"
```

---

### Task 2: Root `Dockerfile` and `.dockerignore`

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: `package.json`, `package-lock.json`, `index.html`, `vite.config.js`, `src/`, `public/`, `backend/requirements.txt`, `backend/` (from Task 1).
- Produces: a buildable image tagged locally as `acrn-adjudication:verify` for later tasks' end-to-end tests. Runtime contract: listens on container port `8000`, serves `/health` and the SPA, `CMD` is `uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000`.

- [ ] **Step 1: Confirm the build currently fails (no Dockerfile yet)**

Run from the repo root:
```
docker build -t acrn-adjudication:verify .
```
Expected: FAIL — `no such file or directory` / `Dockerfile: no such file or directory`, or Docker uses a stale/nonexistent Dockerfile reference. Either way, there is currently nothing to build.

- [ ] **Step 2: Create `.dockerignore`**

Create `.dockerignore` at the repo root:

```
node_modules
.git
.gitignore
.idea
dist
venv
.venv
__pycache__
*.pyc
*.pyo
*.db
*.csv
*.docx
*.xlsx
*.pdf
Supporting SOPs
Supporting resources
Suggested architecture
Prompts and workflow
docs
uploads
```

- [ ] **Step 3: Create the multi-stage `Dockerfile`**

Create `Dockerfile` at the repo root:

```dockerfile
# syntax=docker/dockerfile:1

# ---- Stage 1: build the React/Vite frontend ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---- Stage 2: Python runtime serving the API + built SPA ----
FROM python:3.12.2-slim AS runtime
WORKDIR /app

RUN groupadd --system acrn && useradd --system --gid acrn --home /app acrn

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY --from=frontend /build/dist ./dist

RUN mkdir -p /app/uploads && chown -R acrn:acrn /app

USER acrn
EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Build the image and verify it succeeds**

Run:
```
docker build -t acrn-adjudication:verify .
```
Expected: build completes successfully (both stages). If `pip install` fails trying to compile `numpy`/`pandas`/`psycopg2-binary` from source (no prebuilt wheel found for `cp312` on this base image), add `build-essential` and `libpq-dev` to the runtime stage right before the `pip install` line:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
```
placed immediately before `COPY backend/requirements.txt ./backend/requirements.txt`. Re-run the build after adding this if needed.

- [ ] **Step 5: Run the backend test suite inside the built image**

This is the backend verification that could not run on the host (host only has Python 3.14; the image is pinned to 3.12 matching `runtime.txt`):
```
docker run --rm acrn-adjudication:verify python -m pytest backend/tests -q
```
Expected: all tests pass (the architecture guide records 146 backend tests at last verification; the count may differ slightly with Task 1's two new tests included).

- [ ] **Step 6: Boot the container standalone and hit `/health`**

```
docker run --rm -d --name acrn-verify -p 18005:8000 acrn-adjudication:verify
```
Wait 2 seconds, then:
```
curl -sf http://localhost:18005/health
```
Expected: JSON containing `"status": "ok"` and `"service": "ACRN Adjudication API"`. Then verify the SPA is served for a non-API path:
```
curl -sf http://localhost:18005/
```
Expected: HTML containing `<div id="root">` and the title `ACRN Adjudicate — PROTECT-Africa Clinical Adjudication Platform`. Clean up:
```
docker stop acrn-verify
```

- [ ] **Step 7: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "build: add multi-stage Docker image (frontend build + FastAPI runtime)"
```

---

### Task 3: Base `docker-compose.yml`

**Files:**
- Modify: `docker-compose.yml` (full rewrite — replaces the current `db`+`api` definition, which referenced a nonexistent `backend/Dockerfile`)

**Interfaces:**
- Consumes: `Dockerfile` (Task 2), the image's `EXPOSE 8000` / `/health` contract.
- Produces: a service named `app` that later override files (`docker-compose.dev.yml`, `docker-compose.prod.yml`, `docker-compose.localdb.yml`) extend by adding `environment`, `env_file`, and (for localdb) a `db` dependency.

- [ ] **Step 1: Verify the current file is broken**

Run:
```
docker compose config
```
Expected: it parses (the old file is valid YAML) but references `build: ./backend` with no `backend/Dockerfile` — a subsequent `docker compose build` would fail. This confirms the file needs replacing, not patching.

- [ ] **Step 2: Rewrite `docker-compose.yml`**

Replace the entire contents of `docker-compose.yml` with:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${APP_PORT:-8005}:8000"
    volumes:
      - uploads:/app/uploads
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

volumes:
  uploads:
```

- [ ] **Step 3: Verify the base config is valid**

Run:
```
docker compose config
```
Expected: valid rendered YAML with one service `app` (no `db`), port mapping defaulting to `8005:8000`.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "build: rewrite base compose file for the single app image"
```

---

### Task 4: Environment overrides — `docker-compose.dev.yml`, `docker-compose.prod.yml`, `docker-compose.localdb.yml`

**Files:**
- Create: `docker-compose.dev.yml`
- Create: `docker-compose.prod.yml`
- Create: `docker-compose.localdb.yml`

**Interfaces:**
- Consumes: `app` service from `docker-compose.yml` (Task 3).
- Produces: three named compose combinations that Task 6's scripts invoke: `(yml, dev.yml)`, `(yml, prod.yml)`, `(yml, localdb.yml)`.

- [ ] **Step 1: Create `docker-compose.dev.yml`**

```yaml
services:
  app:
    env_file:
      - .env.dev
    environment:
      ENVIRONMENT: development
      ENABLE_DEMO_ACCOUNTS: "true"
      AUTH_COOKIE_SECURE: "true"
```

- [ ] **Step 2: Create `docker-compose.prod.yml`**

```yaml
services:
  app:
    env_file:
      - .env.prod
    environment:
      ENVIRONMENT: production
      ENABLE_DEMO_ACCOUNTS: "false"
      AUTH_COOKIE_SECURE: "true"
    restart: always
```

- [ ] **Step 3: Create `docker-compose.localdb.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: acrn_adjudication
      POSTGRES_USER: acrn_user
      POSTGRES_PASSWORD: acrn_local_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U acrn_user -d acrn_adjudication"]
      interval: 5s
      timeout: 5s
      retries: 10

  app:
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://acrn_user:acrn_local_password@db:5432/acrn_adjudication
      DB_SSL_MODE: disable
      ENVIRONMENT: development
      ENABLE_DEMO_ACCOUNTS: "true"
      AUTH_COOKIE_SECURE: "false"
      SECRET_KEY: local-dev-secret-change-me

volumes:
  pgdata:
```

- [ ] **Step 4: Verify each override renders**

Run each and inspect the merged output for correctness (dev/prod should show one `app` service with the respective `env_file`; localdb should show two services, `app` depending on `db`):
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.localdb.yml config
```
Expected: all three render valid YAML with no errors. The dev/prod renders will show `env_file` load warnings if `.env.dev`/`.env.prod` don't exist yet — that's expected until Task 5.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.dev.yml docker-compose.prod.yml docker-compose.localdb.yml
git commit -m "build: add dev, prod, and local-db compose overrides"
```

---

### Task 5: Env templates and `.gitignore`

**Files:**
- Create: `.env.dev.example`
- Create: `.env.prod.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the full list of env vars read by the backend (`DATABASE_URL`, `DB_SSL_MODE` from Task 1, `SECRET_KEY`, `OPENAI_API_KEY`, `SESSION_HOURS`, `LOGIN_LOCK_AFTER`, `LOGIN_LOCK_MINUTES`, `DEMO_DEFAULT_PASSWORD`, `DEMO_FORCE_PASSWORD_CHANGE`, `RT_PSEUDONYM_SECRET`, `RT_IDENTITY_ENCRYPTION_KEY`).
- Produces: `.env.dev.example` / `.env.prod.example` that Task 6's scripts check for a corresponding real `.env.dev` / `.env.prod` before deploying.

- [ ] **Step 1: Create `.env.dev.example`**

```
# ACRN Adjudication -- DEV environment
# Copy this file to .env.dev and fill in real values. Never commit .env.dev.

APP_PORT=8005

# External dev Postgres (ACRN-managed). SSL is required.
DATABASE_URL=postgresql://USERNAME:PASSWORD@DEV_DB_HOST:5432/acrn_adjudication
DB_SSL_MODE=require

SECRET_KEY=change-me-dev-secret
OPENAI_API_KEY=

SESSION_HOURS=12
LOGIN_LOCK_AFTER=5
LOGIN_LOCK_MINUTES=15

DEMO_DEFAULT_PASSWORD=ACRN@2026
DEMO_FORCE_PASSWORD_CHANGE=true

RT_PSEUDONYM_SECRET=change-me-dev-pseudonym-secret
RT_IDENTITY_ENCRYPTION_KEY=
```

- [ ] **Step 2: Create `.env.prod.example`**

```
# ACRN Adjudication -- PRODUCTION environment
# Copy this file to .env.prod and fill in real values. Never commit .env.prod.

APP_PORT=8005

# External production Postgres (ACRN-managed). SSL is required.
DATABASE_URL=postgresql://USERNAME:PASSWORD@PROD_DB_HOST:5432/acrn_adjudication
DB_SSL_MODE=require

SECRET_KEY=
OPENAI_API_KEY=

SESSION_HOURS=12
LOGIN_LOCK_AFTER=5
LOGIN_LOCK_MINUTES=15

RT_PSEUDONYM_SECRET=
RT_IDENTITY_ENCRYPTION_KEY=
```

- [ ] **Step 3: Update `.gitignore`**

The current `.gitignore` ends with:

```
# OS/editor noise
.DS_Store
Thumbs.db
```

Append (use the Edit tool, appending after the existing content):

```

# Environment secrets (real values -- never commit)
.env
.env.dev
.env.prod
.env.local
```

- [ ] **Step 4: Verify git ignores real env files but tracks the examples**

```bash
cp .env.dev.example .env.dev
git status --porcelain .env.dev .env.dev.example
```
Expected: `.env.dev.example` shows as untracked/staged (new file), `.env.dev` does not appear at all (ignored). Then remove the throwaway copy:
```bash
rm .env.dev
```

- [ ] **Step 5: Commit**

```bash
git add .env.dev.example .env.prod.example .gitignore
git commit -m "build: add dev/prod env templates and ignore real env files"
```

---

### Task 6: Deploy scripts (dev, prod, local) and end-to-end verification

**Files:**
- Create: `scripts/deploy-dev.sh`
- Create: `scripts/deploy-dev.ps1`
- Create: `scripts/deploy-prod.sh`
- Create: `scripts/deploy-prod.ps1`
- Create: `scripts/deploy-local.sh`
- Create: `scripts/deploy-local.ps1`

**Interfaces:**
- Consumes: `docker-compose.yml` + the three overrides (Tasks 3–4), `.env.dev.example` / `.env.prod.example` (Task 5).
- Produces: the one-command entry points named directly in the README (Task 7): `./scripts/deploy-dev.sh`, `./scripts/deploy-prod.sh`, `./scripts/deploy-local.sh` (and `.ps1` equivalents).

- [ ] **Step 1: Create `scripts/deploy-dev.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.dev ]; then
  echo "Error: .env.dev not found. Copy .env.dev.example to .env.dev and fill in real values." >&2
  exit 1
fi

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

echo "Deployed. Waiting for health check..."
for i in $(seq 1 20); do
  if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps app | grep -q "healthy"; then
    echo "app is healthy."
    break
  fi
  sleep 3
done

PORT=$(grep -E '^APP_PORT=' .env.dev | cut -d= -f2)
PORT=${PORT:-8005}
echo "Dev deployment is live on port ${PORT} (edge routes https://adjudication-dev.acrncloud.com/ here)."
```

- [ ] **Step 2: Create `scripts/deploy-prod.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.prod ]; then
  echo "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values." >&2
  exit 1
fi

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "Deployed. Waiting for health check..."
for i in $(seq 1 20); do
  if docker compose -f docker-compose.yml -f docker-compose.prod.yml ps app | grep -q "healthy"; then
    echo "app is healthy."
    break
  fi
  sleep 3
done

PORT=$(grep -E '^APP_PORT=' .env.prod | cut -d= -f2)
PORT=${PORT:-8005}
echo "Prod deployment is live on port ${PORT} (edge routes https://adjudication.acrncloud.com/ here)."
```

- [ ] **Step 3: Create `scripts/deploy-local.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose -f docker-compose.yml -f docker-compose.localdb.yml up -d --build

echo "Deployed. Waiting for health check..."
for i in $(seq 1 20); do
  if docker compose -f docker-compose.yml -f docker-compose.localdb.yml ps app | grep -q "healthy"; then
    echo "app is healthy."
    break
  fi
  sleep 3
done

echo "Local deployment (bundled Postgres) is live at http://localhost:8005/"
```

- [ ] **Step 4: Create `scripts/deploy-dev.ps1`**

```powershell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.dev")) {
    Write-Error "Error: .env.dev not found. Copy .env.dev.example to .env.dev and fill in real values."
    exit 1
}

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.dev.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        break
    }
    Start-Sleep -Seconds 3
}

$portLine = Select-String -Path ".env.dev" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Dev deployment is live on port $port (edge routes https://adjudication-dev.acrncloud.com/ here)."
```

- [ ] **Step 5: Create `scripts/deploy-prod.ps1`**

```powershell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.prod")) {
    Write-Error "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
    exit 1
}

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.prod.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        break
    }
    Start-Sleep -Seconds 3
}

$portLine = Select-String -Path ".env.prod" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Prod deployment is live on port $port (edge routes https://adjudication.acrncloud.com/ here)."
```

- [ ] **Step 6: Create `scripts/deploy-local.ps1`**

```powershell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

docker compose -f docker-compose.yml -f docker-compose.localdb.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.localdb.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        break
    }
    Start-Sleep -Seconds 3
}

Write-Host "Local deployment (bundled Postgres) is live at http://localhost:8005/"
```

- [ ] **Step 7: Make the shell scripts executable and stage the bit for git**

```bash
chmod +x scripts/deploy-dev.sh scripts/deploy-prod.sh scripts/deploy-local.sh
git add scripts/deploy-dev.sh scripts/deploy-prod.sh scripts/deploy-local.sh scripts/deploy-dev.ps1 scripts/deploy-prod.ps1 scripts/deploy-local.ps1
git update-index --chmod=+x scripts/deploy-dev.sh scripts/deploy-prod.sh scripts/deploy-local.sh
```

- [ ] **Step 8: End-to-end verification — run the local deploy script for real**

This is the full-system test: build, boot with a real (throwaway) Postgres, confirm health and the SPA both respond, confirm the app actually talks to Postgres (not the SQLite fallback), then tear down.

```bash
./scripts/deploy-local.sh
```
Expected: script prints `app is healthy.` and the final `http://localhost:8005/` line.

```bash
curl -sf http://localhost:8005/health
```
Expected: JSON with `"status": "ok"`.

```bash
curl -sf http://localhost:8005/
```
Expected: HTML containing `<div id="root">`.

```bash
docker compose -f docker-compose.yml -f docker-compose.localdb.yml logs app | grep -i "postgresql connection established"
```
Expected: a log line confirming Postgres (not SQLite fallback) was used — proving the `db` dependency and `DATABASE_URL` wiring in `docker-compose.localdb.yml` work end-to-end.

Tear down:
```bash
docker compose -f docker-compose.yml -f docker-compose.localdb.yml down -v
```

- [ ] **Step 9: Commit**

```bash
git add scripts/deploy-dev.sh scripts/deploy-dev.ps1 scripts/deploy-prod.sh scripts/deploy-prod.ps1 scripts/deploy-local.sh scripts/deploy-local.ps1
git commit -m "build: add one-command dev/prod/local deploy scripts"
```

---

### Task 7: README rewrite

**Files:**
- Modify: `README.md` (full rewrite — current file is a 2-line stub)

**Interfaces:**
- Consumes: facts established in Tasks 1–6 (env vars, script names, ports, URLs) and the existing `ACRN_APP_COMPLETE_FUNCTION_AND_ARCHITECTURE_GUIDE.md` / `DEMO_ACCOUNTS.md` for functionality/portal/demo-account content.
- Produces: the final documentation deliverable. Nothing downstream depends on it.

- [ ] **Step 1: Replace `README.md` in full**

```markdown
# ACRN Adjudication Platform

Role-separated clinical operations system for the ACRN PROTECT-Africa (EOPE, A202501 v1.2) and LOPE-Nigeria (ACRN-202503 v1.1) studies. It turns blinded study evidence into a controlled, independently reviewed, signed and auditable endpoint determination -- while keeping administration, quality control and clinical judgment separate.

> Standards referenced: ICH E6(R2) GCP, 21 CFR Part 11, EU Annex 11, GAMP 5.

## The problem it solves

A site records blood pressure, labs, ultrasound findings, medications, delivery information and other source evidence -- but that evidence is not automatically a final clinical endpoint. Independent reviewers assess it under a defined charter and rules, and disagreements route to a committee. The platform:

- imports or demonstrates blinded evidence and standardises source fields into canonical clinical fields;
- calculates deterministic DV-01 through DV-30 clinical-support variables;
- checks whether required evidence is complete and prevents an unjustifiably high certainty classification;
- lets two independent reviewers work without seeing one another's in-flight answers;
- routes discordant answers to a committee, and records signatures and locked outcomes;
- gives Monitor/QC staff operational oversight without adjudication authority; and
- gives administrators configuration and access control without clinical decision authority.

**The system may organise and derive facts from evidence, but the adjudicator makes the clinical determination.** A pre-existing "PE status" or diagnosis value in an imported file is never used to determine the endpoint -- that would defeat the purpose of independent adjudication.

## The three portals

| Portal | Route | Purpose |
|---|---|---|
| **Adjudicator** | `/` | Subject queue, eSource/evidence review, DV support display, narrative, determination + signature, locked eTMF record, committee review. |
| **Monitor/QC** | `/monitor` | Operational oversight from import through reconciliation, packet prep, pre-QC, reviewer assignment, final QC and release. Cannot see in-flight reviewer decisions or alter determinations. |
| **Admin** | `/admin` | Users, roles, studies, sites, DV rules, canonical mappings, forms/templates, workflow configuration, integrations, audit trail, access reviews, reports. No clinical case access. |

## Architecture

```text
Browser
  |
  |-- React + Vite single-page frontend
  |     |-- Demo login and portal selector
  |     |-- Adjudicator / Monitor-QC / Admin workspaces
  |     `-- Local DV display engine
  |
  `-- HTTP / JSON
        |
        `-- FastAPI backend (single process, serves the built SPA too)
              |-- Import & field-mapping APIs
              |-- Reconciliation & derivation APIs
              |-- Narrative & report generation
              |-- Reviewer & committee submissions
              |-- Workflow gates & audit APIs
              |-- Admin & Monitor role checks
              |-- Python authoritative clinical services
              `-- SQLAlchemy models
                     |
                     `-- PostgreSQL (falls back to local SQLite when Postgres is unreachable)
```

Frontend entry point: `src/main.jsx` / `src/App.jsx`. Backend entry point: `backend/main.py`, which mounts 15 routers and serves the built `dist/` SPA for any non-`/api` route.

## Tech stack

- **Frontend:** React 18, Vite 5, `lucide-react` icons.
- **Backend:** FastAPI, SQLAlchemy 2, Pydantic 2, Uvicorn.
- **Database:** PostgreSQL 16 (SQLite fallback for offline/demo use).
- **Security/auth:** `python-jose`, `passlib[bcrypt]` (demo session auth today; production requires Microsoft Entra ID -- see Limitations).
- **Document generation:** ReportLab (PDF), `python-docx`.
- **AI narrative:** OpenAI API (optional -- narrative falls back to a local rule-based generator when no key is configured).
- **Testing:** `pytest`, `pytest-asyncio` (backend); Vite build (frontend).

## Backend API groups

15 routers, 67 endpoints, mounted under `/api` (interactive docs at `/api/docs` and `/api/redoc`):

- `/api/import` -- EDC/eSource import, batch listing. Validates required columns, blocks blinded columns, never lets eSource overwrite EDC values.
- `/api/mappings` -- canonical field-mapping retrieval and creation.
- `/api/reconcile` -- source-value reconciliation and discrepancy flagging.
- `/api/derive`, inline derivation -- deterministic DV-01--DV-30 clinical-support calculations.
- `/api/narrative` -- narrative generation/retrieval/edit logging.
- `/api/adjudication` -- reviewer submission with visibility-controlled status.
- `/api/committee` -- final committee locking.
- `/api/audit` -- audit trail retrieval.
- `/api/export` -- PDF and canonical CSV output.
- `/api/auth` -- session login/logout, user administration.
- `/api/admin` -- role-protected administration (users, roles, studies, sites, rules, mappings, forms, workflow versions, integrations, audit, access reviews, reports).
- `/api/monitor` -- role- and study-scope-protected operational monitoring.
- `/api/realtime` -- RealTime long-form CSV safety layer / longitudinal database.
- `/api/workflow` -- QA release, state retrieval, controlled transitions, reviewer view, concordance.

## Local development (without Docker)

```bash
# frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000

# backend (separate terminal, Python 3.12)
cd backend
python -m venv venv && source venv/bin/activate   # or scripts/activate_venv.*
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Demo accounts (local demo mode only -- see [DEMO_ACCOUNTS.md](DEMO_ACCOUNTS.md)):

| Email | Role |
|---|---|
| admin@acrnhealth.com | Admin |
| monitor1@acrnhealth.com / monitor2@acrnhealth.com | Monitor |
| adjudicatora / b / c @acrnhealth.com | Adjudicator |

## Docker deployment

The app ships as a single Docker image: a multi-stage build compiles the React SPA and bundles it with the FastAPI backend on Python 3.12. Postgres is **external** (ACRN-managed) -- the container never runs a database in dev/prod.

| Environment | URL | Server | Command |
|---|---|---|---|
| Development | https://adjudication-dev.acrncloud.com/ | ACRN dev Oracle server | `./scripts/deploy-dev.sh` |
| Production | https://adjudication.acrncloud.com/ | ACRN prod Oracle server | `./scripts/deploy-prod.sh` |

On Windows, use the `.ps1` equivalents (`scripts/deploy-dev.ps1`, `scripts/deploy-prod.ps1`).

### One-time setup per server

```bash
cp .env.dev.example .env.dev     # (or .env.prod.example .env.prod on the prod server)
# edit .env.dev / .env.prod with real DATABASE_URL, SECRET_KEY, OPENAI_API_KEY, etc.
```

Then deploy:

```bash
./scripts/deploy-dev.sh     # dev server
./scripts/deploy-prod.sh    # prod server
```

Both commands build the image, start the `app` container bound to host port `8005` (override via `APP_PORT`), and wait for `/health` to report healthy. The server's existing reverse proxy/load balancer terminates HTTPS for the public domain and forwards plain HTTP to this port -- no TLS container is included in this stack.

### Local development with a bundled Postgres (no external DB access)

```bash
./scripts/deploy-local.sh    # or deploy-local.ps1 on Windows
```

Starts `app` plus a throwaway `postgres:16-alpine` container (`docker-compose.localdb.yml`), reachable at `http://localhost:8005/`. Not used on the ACRN servers.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `APP_PORT` | no (default `8005`) | Host port the app is published on. |
| `DATABASE_URL` | yes | External Postgres connection string (`postgresql://user:pass@host:5432/db`). |
| `DB_SSL_MODE` | yes in dev/prod | Postgres SSL mode, e.g. `require`. Passed through to `psycopg2` as `connect_args={"sslmode": ...}`. |
| `SECRET_KEY` | yes | Session/token signing key. |
| `OPENAI_API_KEY` | no | Enables AI-assisted narrative generation; falls back to the local rule-based generator when unset. |
| `SESSION_HOURS` | no (default `12`) | Session lifetime. |
| `LOGIN_LOCK_AFTER` / `LOGIN_LOCK_MINUTES` | no (default `5` / `15`) | Login lockout policy. |
| `ENABLE_DEMO_ACCOUNTS` | no (default `false`) | Seeds the fixed demo accounts on startup. Set `true` in dev, `false` in prod. |
| `DEMO_DEFAULT_PASSWORD` | no | Shared local demo password (dev only). |
| `DEMO_FORCE_PASSWORD_CHANGE` | no | Forces a password change on first demo login. |
| `AUTH_COOKIE_SECURE` | yes | Set `true` behind HTTPS (both dev and prod, since the edge terminates TLS). |
| `RT_PSEUDONYM_SECRET` | yes | Pseudonymization secret for the RealTime import pipeline. |
| `RT_IDENTITY_ENCRYPTION_KEY` | no | Identity encryption key for the RealTime pipeline. |

## What is fully functional today

- Role-specific demo entry into all three portals, with frontend access-denied handling for mismatched roles.
- Subject loading, selection, search and navigation.
- Synthetic and supported CSV case creation with safety checks.
- Deterministic DV support calculations and completeness/certainty gates.
- Evidence, narrative, source-document, query and recusal demonstrations.
- Determination entry and local signing/locking flow.
- Committee comparison, adoption and locking demonstration.
- PDF and CSV backend exports.
- Admin navigation, filters, registers, exports and governed-action simulations.
- Monitor queues, operational controls and safe status displays.
- Backend models and endpoints for import, derivation, reviewer submission, committee, workflow, admin and monitor operations.
- RealTime streaming classification foundation.
- Automated regression and security tests.

## What is simulated in demo mode

Email/password authentication, OTP/step-up auth, most Admin/Monitor mutations (shown via prompts/confirmations), external connection tests, notification delivery, eTMF transfer, and live EDC/eSource/LIMS/SharePoint/Entra connections. Synthetic data is visibly labelled and must never be mixed with production data.

## Production hardening still required

Before live regulated use: Microsoft Entra ID integration with validated authorization claims, production-grade session/token handling, genuine MFA/step-up electronic signature, complete API authorization coverage on every clinical endpoint, secure object storage with malware scanning, approved EDC/eSource/LIMS/SharePoint/eTMF/notification adapters, background/restart-safe ingestion for large extracts, an approved secret vault with key rotation, backup/recovery/retention/legal-hold procedures, telemetry/alerting/incident management, formal user-acceptance/validation/accessibility testing, and quality-system + regulatory assessment.

## Repository layout

```
backend/        FastAPI app, models, services, migrations, tests
src/            React SPA source
scripts/        Docker deploy scripts + local venv helpers
docs/           Design specs and implementation plans
Dockerfile      Multi-stage build (frontend -> backend runtime image)
docker-compose.yml            Base app service
docker-compose.dev.yml        Dev overrides (external dev Postgres)
docker-compose.prod.yml       Prod overrides (external prod Postgres)
docker-compose.localdb.yml    Optional bundled Postgres for offline local dev
```
```

- [ ] **Step 2: Sanity-check the rendered markdown**

Open `README.md` and confirm: no leftover placeholder text, both deploy commands (`deploy-dev.sh`, `deploy-prod.sh`) match the actual filenames from Task 6, and both URLs (`https://adjudication-dev.acrncloud.com/`, `https://adjudication.acrncloud.com/`) are present.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with full functionality, architecture, and deploy guide"
```

---

## Final verification (after all tasks)

- [ ] Run the full local end-to-end flow once more from a clean state to confirm nothing regressed across tasks:
```bash
docker compose -f docker-compose.yml -f docker-compose.localdb.yml down -v --remove-orphans
./scripts/deploy-local.sh
curl -sf http://localhost:8005/health
docker compose -f docker-compose.yml -f docker-compose.localdb.yml down -v
```
Expected: health check passes and the app connects to the bundled Postgres (not the SQLite fallback), exactly as in Task 6 Step 8.
