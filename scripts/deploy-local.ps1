$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

docker compose -f docker-compose.yml -f docker-compose.localdb.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.localdb.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $healthy) {
    Write-Error "app did not become healthy within the timeout. Check 'docker compose -f docker-compose.yml -f docker-compose.localdb.yml logs app'."
    exit 1
}

Write-Host "Local deployment (bundled Postgres) is live at http://localhost:8005/"
