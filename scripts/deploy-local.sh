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
