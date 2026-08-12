# ACRN Adjudication Platform — Docker Deployment Design

**Date:** 2026-08-12
**Status:** Approved (pending written-spec review)
**Scope:** Containerize the app, add one-command dev/prod deploy scripts, support an external SSL Postgres, and rewrite the README. No feature work.

## 1. Goal

Make the platform deployable to two ACRN Oracle servers (dev + prod) with a single command each, backed by an external managed Postgres over SSL, and document the whole system in the README.

- Dev URL: `https://adjudication-dev.acrncloud.com/`
- Prod URL: `https://adjudication.acrncloud.com/`

## 2. Decisions (locked with user)

| Topic | Decision |
|---|---|
| TLS | The ACRN server edge already terminates HTTPS. The container exposes plain HTTP internally. No proxy/TLS container in the stack. |
| Frontend serving | Single app image. FastAPI serves the built `dist/` SPA (existing `main.py` behavior). |
| Dev environment | Mirrors production (built assets, no hot reload). Dev and prod are separate servers. |
| Host port | `8005` on both servers (separate machines, no conflict). Overridable via `APP_PORT`. |
| Database | External managed Postgres, one per environment, via `DATABASE_URL`. SSL required (`DB_SSL_MODE=require`). No DB container in the deploy path. |
| Local DB | Optional opt-in `postgres:16-alpine` container for offline local development only. |
| Migrations | None added. App auto-creates tables via `Base.metadata.create_all` on startup (existing behavior). The 4 SQL files under `backend/migrations/versions` remain additive markers. |
| App code changes | Exactly one, at the DB boundary: `backend/database.py` honors `DB_SSL_MODE`. |

## 3. Topology

```
[ACRN dev server  :8005] ── app (FastAPI + built React SPA) ──▶ external DEV Postgres  (SSL)
[ACRN prod server :8005] ── app (FastAPI + built React SPA) ──▶ external PROD Postgres (SSL)
        (optional) local ── app ──▶ bundled postgres:16 container (SSL disabled)

Browser ──HTTPS──▶ [server edge, terminates TLS] ──HTTP──▶ container :8000
```

One image serves both the JSON API (`/api/*`, `/health`, `/api/docs`) and the SPA (all other routes fall through to `dist/index.html`).

## 4. Files to create / change

### 4.1 `Dockerfile` (repo root, multi-stage)
Build context = repo root (needs both frontend source and `backend/`).

- **Stage `frontend`** — `node:20-alpine`:
  - Copy `package.json`, `package-lock.json`; `npm ci`.
  - Copy `src/`, `public/`, `index.html`, `vite.config.js`; `npm run build` → produces `/app/dist`.
- **Stage `runtime`** — `python:3.12-slim` (matches `runtime.txt` python-3.12.2):
  - Install `backend/requirements.txt` (pinned wheels resolve on cp312).
  - Copy `backend/` → `/app/backend`, and `--from=frontend /app/dist` → `/app/dist`.
  - Create + run as a non-root user; create `/app/uploads`.
  - `EXPOSE 8000`.
  - `CMD ["uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]`.

Container layout `/app/backend/main.py` + `/app/dist/` matches `main.py`'s `dist_path` resolution (`dirname(dirname(__file__))/dist`). If pinned deps fail to find wheels on slim, the plan's fallback is to add `build-essential` + `libpq-dev` to the runtime stage.

### 4.2 `.dockerignore` (repo root)
Exclude from build context: `node_modules/`, `.git/`, `dist/`, `venv/`/`.venv/`, `.idea/`, `__pycache__/`, `*.db`, `*.csv`, `*.docx`, `*.xlsx`, `*.pdf`, `Supporting SOPs/`, `Supporting resources/`, `Suggested architecture/`, `Prompts and workflow/`, `docs/`, `*.md` (except none needed at build). Keeps context small (the repo carries ~1.8 MB of CSVs and many docs).

### 4.3 `docker-compose.yml` (base)
- Service `app`:
  - `build: { context: ., dockerfile: Dockerfile }`
  - `env_file` supplied by the override.
  - `ports: ["${APP_PORT:-8005}:8000"]`
  - `volumes: ["uploads:/app/uploads"]`
  - `healthcheck`: curl/py GET `http://localhost:8000/health`.
  - `restart: unless-stopped`.
- `volumes: { uploads: {} }`
- No `db` service here.

### 4.4 `docker-compose.dev.yml` (override)
- `app.env_file: .env.dev`
- Environment: `ENVIRONMENT=development`, `ENABLE_DEMO_ACCOUNTS=true`, `AUTH_COOKIE_SECURE=true`.
- `APP_PORT` from `.env.dev` (default 8005).

### 4.5 `docker-compose.prod.yml` (override)
- `app.env_file: .env.prod`
- Environment: `ENVIRONMENT=production`, `ENABLE_DEMO_ACCOUNTS=false`, `AUTH_COOKIE_SECURE=true`.
- `restart: always`.

### 4.6 `docker-compose.localdb.yml` (optional override)
- Adds `db` (`postgres:16-alpine`, `pgdata` volume, `pg_isready` healthcheck).
- Overrides `app` to `depends_on: db (healthy)` and sets `DATABASE_URL` to the container, `DB_SSL_MODE=disable`.
- For a developer with no external DB access. Not used on ACRN servers.

### 4.7 One-command scripts (`scripts/`)
Both POSIX (`.sh`, for the Linux Oracle servers) and PowerShell (`.ps1`, for the Windows dev machine):
- `deploy-dev.sh` / `deploy-dev.ps1` → `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
- `deploy-prod.sh` / `deploy-prod.ps1` → prod override equivalent
- `deploy-local.sh` / `deploy-local.ps1` → base + `docker-compose.localdb.yml`

Each script: fails fast if the matching `.env.*` file is missing, prints the resulting URL/port, and tails `app` health.

### 4.8 Env templates
`.env.dev.example` and `.env.prod.example` documenting every var the code reads:
- `APP_PORT=8005`
- `DATABASE_URL=postgresql://USER:PASSWORD@EXTERNAL_HOST:5432/acrn_adjudication`
- `DB_SSL_MODE=require`
- `SECRET_KEY`, `OPENAI_API_KEY`
- `SESSION_HOURS`, `LOGIN_LOCK_AFTER`, `LOGIN_LOCK_MINUTES`
- `DEMO_DEFAULT_PASSWORD`, `DEMO_FORCE_PASSWORD_CHANGE`, `ENABLE_DEMO_ACCOUNTS`
- `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`
- `RT_PSEUDONYM_SECRET`, `RT_IDENTITY_ENCRYPTION_KEY`

Real `.env.dev` / `.env.prod` are git-ignored (never committed).

### 4.9 `.gitignore` update
Add `.env`, `.env.dev`, `.env.prod`, `.env.local` (keep `.env.*.example` tracked).

### 4.10 `backend/database.py` — the one code change
Read `DB_SSL_MODE` and, only when the resolved engine URL is Postgres, pass `connect_args={"sslmode": <value>}` to `create_engine`. SQLite path ignores it. Default when unset: no sslmode arg (preserves current local behavior). Keeps the existing Postgres→SQLite fallback intact.

### 4.11 `README.md` — full rewrite
Sections: one-line summary; the three portals (Adjudicator / Monitor-QC / Admin); architecture diagram; full functionality list (sourced from `ACRN_APP_COMPLETE_FUNCTION_AND_ARCHITECTURE_GUIDE.md`); tech stack; backend API groups (15 routers / 67 endpoints); **Deploy — dev** and **Deploy — prod** (one command each) with the two URLs; env-var reference table; demo accounts; verification status; and the honest production-hardening limitations (Entra ID, MFA e-signature, full API authz coverage, secret vault, backup/retention, formal 21 CFR Part 11 assessment).

## 5. Verification plan

1. Frontend build already passes locally (`npm run build`).
2. `docker compose ... build` succeeds (this is the backend verification that couldn't run locally — pinned 3.12 image).
3. `deploy-local` boots `app` + bundled Postgres; `/health` returns ok; the SPA loads at `http://localhost:8005/`.
4. Confirm SSL wiring: with `DB_SSL_MODE=require` against a non-SSL local DB the connection is rejected (or falls back), proving the flag is applied.

## 6. Out of scope (YAGNI)

- No reverse-proxy / TLS container (edge handles it).
- No Alembic migration runner.
- No feature/UI changes.
- No CORS change (SPA is same-origin with the API).
