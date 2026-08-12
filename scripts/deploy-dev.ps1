$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.dev")) {
    Write-Error "Error: .env.dev not found. Copy .env.dev.example to .env.dev and fill in real values."
    exit 1
}

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.dev.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $healthy) {
    Write-Error "app did not become healthy within the timeout. Check 'docker compose -f docker-compose.yml -f docker-compose.dev.yml logs app'."
    exit 1
}

$portLine = Select-String -Path ".env.dev" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Dev deployment is live on port $port (edge routes https://adjudication-dev.acrncloud.com/ here)."
