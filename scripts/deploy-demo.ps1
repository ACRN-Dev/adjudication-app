# scripts/deploy-demo.ps1
# Deploys the app in demo mode on top of the prod config.
# Run from the repo root on the server.

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".env.prod")) {
    Write-Error "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
    exit 1
}

$composeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.prod.yml", "-f", "docker-compose.demo.yml")

Write-Host "Building demo application image..."
docker compose @composeFiles build
if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }

Write-Host "Applying and verifying database migrations (no data purge)..."
docker compose @composeFiles run --rm --no-deps app python backend/scripts/init_prod.py --schema-only
if ($LASTEXITCODE -ne 0) { throw "Database migration failed; the existing app was not replaced." }

Write-Host "Starting demo deployment with ENABLE_DEMO_ACCOUNTS=true ..."
docker compose @composeFiles up -d
if ($LASTEXITCODE -ne 0) { throw "Docker startup failed." }

Write-Host "Waiting for health check..."
$healthy = $false
for ($i = 1; $i -le 20; $i++) {
    $status = docker compose @composeFiles ps app 2>&1
    if ($status -match "\(healthy\)") {
        Write-Host "App is healthy."
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $healthy) { throw "App did not become healthy within timeout." }

$logs = docker compose @composeFiles logs app 2>&1
if ($logs -match "PostgreSQL unavailable") { throw "App fell back to local SQLite; check the production database settings." }

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
