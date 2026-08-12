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
