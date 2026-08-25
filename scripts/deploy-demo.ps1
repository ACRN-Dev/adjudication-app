# scripts/deploy-demo.ps1
# Deploys the app in demo mode on top of the prod config.
# Run from the repo root on the server.

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".env.prod")) {
    Write-Error "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
    exit 1
}

Write-Host "Starting demo deployment with ENABLE_DEMO_ACCOUNTS=true ..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.demo.yml up -d --build

Write-Host "Waiting for health check..."
$healthy = $false
for ($i = 1; $i -le 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.demo.yml ps app 2>&1
    if ($status -match "\(healthy\)") {
        Write-Host "App is healthy."
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $healthy) {
    Write-Warning "App did not become healthy within timeout. Check logs with: docker compose logs app"
}

Write-Host ""
Write-Host "Demo deployment live at https://adjudication.acrncloud.com" -ForegroundColor Green
Write-Host ""
Write-Host "Demo accounts (password: ACRN@Demo2026):" -ForegroundColor Cyan
Write-Host "  admin@acrnhealth.com          — Admin Portal"
Write-Host "  monitor1@acrnhealth.com       — Monitor Portal (RealTime Imports + Upload)"
Write-Host "  monitor2@acrnhealth.com       — Monitor Portal (QA Reviewer)"
Write-Host "  adjudicatora@acrnhealth.com   — Adjudicator Workbench"
Write-Host "  adjudicatorb@acrnhealth.com   — Adjudicator Workbench"
Write-Host "  chairperson@acrnhealth.com    — Chairperson Portal"
