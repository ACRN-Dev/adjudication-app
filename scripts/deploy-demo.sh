#!/usr/bin/env bash
# scripts/deploy-demo.sh
# Deploys the app in demo mode on top of the prod config.
# Run this from the repo root on the server.
set -euo pipefail
cd "/.."

if [ ! -f .env.prod ]; then
  echo "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values." >&2
  exit 1
fi

echo "Starting demo deployment with ENABLE_DEMO_ACCOUNTS=true ..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.demo.yml up -d --build

echo "Waiting for health check..."
for i in ; do
  if docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.demo.yml ps app | grep -q "(healthy)"; then
    echo "App is healthy."
    break
  fi
  sleep 3
done

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
