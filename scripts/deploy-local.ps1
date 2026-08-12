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
