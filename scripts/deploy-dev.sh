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
