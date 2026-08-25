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

### Microsoft SSO (dev/prod)

On the real ACRN dev/prod servers (`ENABLE_DEMO_ACCOUNTS=false`), only Microsoft Entra ID sign-in is accepted — the demo email/password form is hidden. Anyone in the Entra tenant can sign in: a first sign-in with no matching account auto-provisions one as `ADJUDICATOR`, which reaches only the adjudication workbench and lists nothing until an Admin assigns cases. Existing accounts keep their role, and deactivated accounts stay locked out. See [docs/entra-sso-setup.md](docs/entra-sso-setup.md) for setting up the Azure App Registration and how accounts are created.

## Docker deployment

The app ships as a single Docker image: a multi-stage build compiles the React SPA and bundles it with the FastAPI backend on Python 3.12. Postgres is **external** (ACRN-managed) -- the container never runs a database in dev/prod.

| Environment | URL | Server | Command |
|---|---|---|---|
| Development | https://adjudication-dev.acrncloud.com/ | ACRN dev Oracle server | `./scripts/deploy-dev.sh` |
| Production | https://adjudication.acrncloud.com/ | ACRN prod Oracle server | `./scripts/init-prod.sh` |

On Windows, use the `.ps1` equivalents (`scripts/deploy-dev.ps1`, `scripts/deploy-prod.ps1`).

### One-time setup per server

```bash
cp .env.dev.example .env.dev     # (or .env.prod.example .env.prod on the prod server)
# edit .env.dev / .env.prod with real DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT, SECRET_KEY, OPENAI_API_KEY, etc.
```

Then deploy:

```bash
./scripts/deploy-dev.sh     # dev server
./scripts/deploy-prod.sh    # prod server
```

Both commands build the image, start the `app` container bound to host port `8005` (override via `APP_PORT`), and wait for `/health` to report healthy. The server's existing reverse proxy/load balancer terminates HTTPS for the public domain and forwards plain HTTP to this port -- no TLS container is included in this stack.

### Production runbook

On the production server, `./scripts/init-prod.sh` is the single command for every deployment. It is idempotent, so it is safe to re-run.

**First deployment:**

```bash
git clone <repo-url> adjudication-app && cd adjudication-app
cp .env.prod.example .env.prod
```

Fill in `.env.prod`. The database, Entra SSO and `APP_BASE_URL` settings are required — the script refuses to deploy while any is empty or still holding an example placeholder. Values are read literally, so passwords containing `$`, backticks, `#` or spaces need no quoting.

The two `RT_*` secrets are optional while the RealTime longitudinal import is unused; the script warns and continues. Generate them and store them in the approved secret vault **before the first RealTime import**, since they determine every participant pseudonym:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Preview what will happen to the database without changing anything:

```bash
./scripts/init-prod.sh --dry-run
```

Then deploy:

```bash
./scripts/init-prod.sh
```

**Every later deployment:**

```bash
git pull && ./scripts/init-prod.sh
```

The script validates `.env.prod`, builds the image, runs `backend/scripts/init_prod.py` against the external Postgres, starts the app, and confirms it is healthy and actually connected to Postgres rather than the SQLite fallback. The database step creates the database itself if it does not exist yet, creates missing tables, applies `backend/migrations/versions/*.sql` in order, purges any synthetic `is_demo` rows, provisions the bootstrap administrators, and refuses to finish if no active admin exists or any demo row remains.

Creating the database requires `DB_USER` to hold the `CREATEDB` privilege and to be able to reach the server's `postgres` or `template1` maintenance database. If it can't, the script prints the exact statement for a DBA to run:

```
CREATE DATABASE "acrn_adjudication" OWNER "<DB_USER>";
```

Bootstrap administrators are defined in `BOOTSTRAP_ADMINS` at the top of [backend/scripts/init_prod.py](backend/scripts/init_prod.py). They sign in through Microsoft SSO with no local password, and hold the full `ADMIN` permission set so they can provision everyone else from the Admin Portal. Edit that list to change who gets bootstrap access.

`./scripts/deploy-prod.sh` remains available for a plain rebuild-and-restart with no database work.

**No test data reaches production by default.** `ENABLE_DEMO_ACCOUNTS` is pinned to `false` by `docker-compose.prod.yml`, so demo credentials and header-based authentication are never available there. A dedicated hosted demonstration environment may set `ENABLE_DEMO_DATA=true` to enable resettable synthetic Admin Portal fixtures; authentication remains SSO-only and uses administrator-provisioned users. Leave `ENABLE_DEMO_DATA=false` for live clinical production. Real account management is unaffected — it lives on the separate `/api/auth/users` endpoints.

### Local development with a bundled Postgres (no external DB access)

```bash
./scripts/deploy-local.sh    # or deploy-local.ps1 on Windows
```

Starts `app` plus a throwaway `postgres:16-alpine` container (`docker-compose.localdb.yml`), reachable at `http://localhost:8005/`. Not used on the ACRN servers.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `APP_PORT` | no (default `8005`) | Host port the app is published on. |
| `DB_NAME` | yes | External Postgres database name. |
| `DB_USER` | yes | External Postgres user. |
| `DB_PASSWORD` | yes | External Postgres password. |
| `DB_HOST` | yes | External Postgres host. |
| `DB_PORT` | no (default `5432`) | External Postgres port. |
| `DB_SSL_MODE` | yes in dev/prod | Postgres SSL mode, e.g. `require`. Passed through to `psycopg2` as `connect_args={"sslmode": ...}`. |
| `SECRET_KEY` | no | Reserved for future use — not currently read by the backend. |
| `OPENAI_API_KEY` | no | Enables AI-assisted narrative generation; falls back to the local rule-based generator when unset. |
| `SESSION_HOURS` | no (default `12`) | Session lifetime. |
| `LOGIN_LOCK_AFTER` / `LOGIN_LOCK_MINUTES` | no (default `5` / `15`) | Login lockout policy. |
| `ENABLE_DEMO_ACCOUNTS` | no (default `false`) | Seeds the fixed demo accounts on startup. Set `true` in dev, `false` in prod. |
| `ENABLE_DEMO_DATA` | no (default `false`) | Enables resettable synthetic Admin Portal data without enabling demo-account authentication. Use only in a dedicated demonstration environment. |
| `DEMO_DEFAULT_PASSWORD` | no | Shared local demo password (dev only). |
| `DEMO_FORCE_PASSWORD_CHANGE` | no | Forces a password change on first demo login. |
| `AUTH_COOKIE_SECURE` | yes | Set `true` behind HTTPS (both dev and prod, since the edge terminates TLS). |
| `AUTH_COOKIE_SAMESITE` | no (default `lax` when set, else `none` if `AUTH_COOKIE_SECURE=true`) | Session cookie SameSite policy. Set to `lax` (default in dev/prod compose overrides) since the SPA and API are same-origin. |
| `RT_PSEUDONYM_SECRET` | before the first RealTime import | Keys the HMAC that turns MRN + screening number into a participant pseudonym. **If unset the backend falls back to a value published in this repository**, making pseudonyms reversible by anyone with the source. |
| `RT_IDENTITY_ENCRYPTION_KEY` | before the first RealTime import | Fernet key encrypting the restricted identity crosswalk. If unset it is derived from `RT_PSEUDONYM_SECRET`, inheriting that fallback's weakness. Set both before importing any RealTime data — adding or rotating them later orphans every pseudonym and crosswalk row created without them. |
| `ENTRA_TENANT_ID` | yes on real dev/prod | Microsoft Entra ID tenant ID. See [docs/entra-sso-setup.md](docs/entra-sso-setup.md). |
| `ENTRA_CLIENT_ID` | yes on real dev/prod | Entra App Registration client ID. |
| `ENTRA_CLIENT_SECRET` | yes on real dev/prod | Entra App Registration client secret. |
| `APP_BASE_URL` | yes on real dev/prod | This environment's public HTTPS URL, used to build the SSO redirect URI. |

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
