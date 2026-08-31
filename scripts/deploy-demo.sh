#!/usr/bin/env bash
# scripts/deploy-demo.sh
# Deploys the app in demo mode on top of the prod config.
# Run this from the repo root on the server.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.prod ]; then
  echo "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values." >&2
  exit 1
fi

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.demo.yml"

echo "Building demo application image..."
$COMPOSE build

echo "Applying and verifying database migrations (no data purge)..."
$COMPOSE run --rm --no-deps app python backend/scripts/init_prod.py --schema-only

echo "Starting demo deployment with ENABLE_DEMO_ACCOUNTS=true ..."
$COMPOSE up -d

echo "Waiting for health check..."
healthy=false
for _ in $(seq 1 20); do
  if $COMPOSE ps app | grep -q "(healthy)"; then
    echo "App is healthy."
    healthy=true
    break
  fi
  sleep 3
done

if [ "$healthy" != "true" ]; then
  echo "Error: app did not become healthy. Check '$COMPOSE logs app'." >&2
  exit 1
fi

if $COMPOSE logs app 2>&1 | grep -qi "PostgreSQL unavailable"; then
  echo "Error: app fell back to local SQLite; check the production database settings." >&2
  exit 1
fi

echo ""
echo "Demo deployment live at https://adjudication.acrncloud.com"
echo ""
echo "Demo accounts (password: ACRN@Demo2026):"
echo "  admin@acrnhealth.com          — Admin Portal"
echo "  monitor1@acrnhealth.com       — Monitor Portal (RealTime Imports + Upload)"
echo "  monitor2@acrnhealth.com       — Monitor Portal (QA Reviewer)"
echo "  adjudicatora@acrnhealth.com   — Adjudicator Workbench"
echo "  adjudicatorb@acrnhealth.com   — Adjudicator Workbench"
echo "  chairperson@acrnhealth.com    — Chairperson Portal"
