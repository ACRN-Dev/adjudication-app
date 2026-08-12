$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.prod")) {
    Write-Error "Error: .env.prod not found. Copy .env.prod.example to .env.prod and fill in real values."
    exit 1
}

Get-Content ".env.prod" | Where-Object { $_ -match '^\s*[^#][^=]*=' } | ForEach-Object {
    $name, $value = $_.Split('=', 2)
    [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
}

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed (exit code $LASTEXITCODE)."
    exit 1
}

Write-Host "Deployed. Waiting for health check..."
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose -f docker-compose.yml -f docker-compose.prod.yml ps app
    if ($status -match "\(healthy\)") {
        Write-Host "app is healthy."
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $healthy) {
    Write-Error "app did not become healthy within the timeout. Check 'docker compose -f docker-compose.yml -f docker-compose.prod.yml logs app'."
    exit 1
}

$logs = docker compose -f docker-compose.yml -f docker-compose.prod.yml logs app 2>&1
if ($logs -match "PostgreSQL unavailable") {
    Write-Error "app fell back to local SQLite - check DATABASE_URL / DB_SSL_MODE in .env.prod."
    exit 1
}

$portLine = Select-String -Path ".env.prod" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Prod deployment is live on port $port (edge routes https://adjudication.acrncloud.com/ here)."
