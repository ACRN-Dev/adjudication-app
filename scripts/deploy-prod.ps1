$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.prod")) {
    Write-Error "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
    exit 1
}

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host "Deployed. Waiting for health check..."
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.prod.yml ps app
    if ($status -match "healthy") {
        Write-Host "app is healthy."
        break
    }
    Start-Sleep -Seconds 3
}

$portLine = Select-String -Path ".env.prod" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Prod deployment is live on port $port (edge routes https://adjudication.acrncloud.com/ here)."
