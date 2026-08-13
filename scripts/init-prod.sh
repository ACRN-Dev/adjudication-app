#!/usr/bin/env bash
#
# Full production initialisation. Run this on the production server after `git pull`.
#
#   ./scripts/init-prod.sh              # validate, build, initialise the DB, start the app
#   ./scripts/init-prod.sh --dry-run    # validate and preview the DB changes, change nothing
#
# Every step is idempotent, so this is safe to re-run on each deployment.
# For a plain redeploy with no database work, use ./scripts/deploy-prod.sh instead.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
DRY_RUN=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN="--dry-run"
fi

fail() { echo "" >&2; echo "ERROR: $*" >&2; exit 1; }

# ── 1. Environment file ─────────────────────────────────────────────────────────────
echo "[1/5] Validating .env.prod"

if [ ! -f .env.prod ]; then
  fail ".env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
fi

set -a
# shellcheck disable=SC1091
source .env.prod
set +a

REQUIRED=(
  DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT DB_SSL_MODE
  ENTRA_TENANT_ID ENTRA_CLIENT_ID ENTRA_CLIENT_SECRET APP_BASE_URL
  RT_PSEUDONYM_SECRET RT_IDENTITY_ENCRYPTION_KEY
)
# Values carried over verbatim from .env.prod.example -- a filled-in file has none of these.
PLACEHOLDERS=("USERNAME" "PASSWORD" "PROD_DB_HOST" "DEV_DB_HOST" "change-me" "change-me-dev-secret" "change-me-dev-pseudonym-secret")

missing=()
placeholder=()
for name in "${REQUIRED[@]}"; do
  value="${!name:-}"
  if [ -z "$value" ]; then
    missing+=("$name")
    continue
  fi
  for bad in "${PLACEHOLDERS[@]}"; do
    if [ "$value" = "$bad" ]; then
      placeholder+=("$name")
      break
    fi
  done
done

if [ ${#missing[@]} -gt 0 ]; then
  fail "These required settings are empty or absent from .env.prod: ${missing[*]}"
fi
if [ ${#placeholder[@]} -gt 0 ]; then
  fail "These settings still hold example placeholder values: ${placeholder[*]}"
fi

case "$APP_BASE_URL" in
  https://*) ;;
  *) fail "APP_BASE_URL must be an https:// URL (got '$APP_BASE_URL'). Microsoft SSO will not redirect to plain http." ;;
esac

case "$APP_BASE_URL" in
  */) fail "APP_BASE_URL must not end with a trailing slash (got '$APP_BASE_URL')." ;;
esac

# Fernet keys are exactly 32 random bytes in url-safe base64: 43 chars plus '='.
if ! printf '%s' "$RT_IDENTITY_ENCRYPTION_KEY" | grep -Eq '^[A-Za-z0-9_-]{43}=$'; then
  fail "RT_IDENTITY_ENCRYPTION_KEY is not a valid Fernet key. Generate one with:
       python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
fi

if [ "$(printf '%s' "${ENABLE_DEMO_ACCOUNTS:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
  fail "ENABLE_DEMO_ACCOUNTS is set to true in .env.prod. Demo accounts and synthetic Admin Portal
       fixtures must stay disabled in production. Remove that line."
fi

echo "      Target database: ${DB_NAME} at ${DB_HOST}:${DB_PORT} (sslmode=${DB_SSL_MODE})"
echo "      Public URL:      ${APP_BASE_URL}"
echo "      SSO callback:    ${APP_BASE_URL}/api/auth/sso/callback"

# ── 2. Build ────────────────────────────────────────────────────────────────────────
echo ""
echo "[2/5] Building the application image"
$COMPOSE build

# ── 3. Initialise the database ──────────────────────────────────────────────────────
echo ""
echo "[3/5] Initialising the production database"
$COMPOSE run --rm --no-deps app python backend/scripts/init_prod.py $DRY_RUN

if [ -n "$DRY_RUN" ]; then
  echo ""
  echo "Dry run complete. The application was not started. Re-run without --dry-run to deploy."
  exit 0
fi

# ── 4. Start ────────────────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Starting the application"
$COMPOSE up -d

# ── 5. Verify ───────────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Waiting for the health check"
healthy=false
for _ in $(seq 1 20); do
  if $COMPOSE ps app | grep -q "(healthy)"; then
    healthy=true
    break
  fi
  sleep 3
done

if [ "$healthy" != "true" ]; then
  fail "The app did not become healthy within the timeout. Check '$COMPOSE logs app'."
fi
echo "      app is healthy."

if $COMPOSE logs app 2>&1 | grep -qi "PostgreSQL unavailable"; then
  fail "The app fell back to local SQLite instead of the production Postgres.
       Check DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT / DB_SSL_MODE in .env.prod."
fi
echo "      app is connected to the production Postgres."

echo ""
echo "Production deployment is live on port ${APP_PORT:-8005} (edge routes ${APP_BASE_URL} here)."
echo "Sign in at ${APP_BASE_URL} using Sign in with Microsoft:"
echo "  - emmanuel.buruvuru@acrnhealth.com"
echo "  - tinotenda.chibongore@acrnhealth.com"
echo "Provision everyone else from the Admin Portal's user management screen."
