#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.dev ]; then
  echo "Error: .env.dev not found. Copy .env.dev.example to .env.dev and fill in real values." >&2
  exit 1
fi

set -a
source .env.dev
set +a

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

echo "Deployed. Waiting for health check..."
healthy=false
for i in $(seq 1 20); do
  if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps app | grep -q "(healthy)"; then
    echo "app is healthy."
    healthy=true
    break
  fi
  sleep 3
done

if [ "$healthy" != "true" ]; then
  echo "Error: app did not become healthy within the timeout. Check 'docker compose -f docker-compose.yml -f docker-compose.dev.yml logs app'." >&2
  exit 1
fi

if docker compose -f docker-compose.yml -f docker-compose.dev.yml logs app 2>&1 | grep -qi "PostgreSQL unavailable"; then
  echo "Error: app fell back to local SQLite — check DATABASE_URL / DB_SSL_MODE in .env.dev." >&2
  exit 1
fi

PORT=$(grep -E '^APP_PORT=' .env.dev | cut -d= -f2 || true)
PORT=${PORT:-8005}
echo "Dev deployment is live on port ${PORT} (edge routes https://adjudication-dev.acrncloud.com/ here)."
