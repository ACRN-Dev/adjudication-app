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

$composeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.prod.yml")

Write-Host "Building application image..."
docker compose @composeFiles build
if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }

Write-Host "Applying and verifying database migrations (no data purge)..."
docker compose @composeFiles run --rm --no-deps app python backend/scripts/init_prod.py --schema-only
if ($LASTEXITCODE -ne 0) { throw "Database migration failed; the existing app was not replaced." }

Write-Host "Starting application..."
docker compose @composeFiles up -d
if ($LASTEXITCODE -ne 0) { throw "Docker startup failed." }

Write-Host "Deployed. Waiting for health check..."
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    $status = docker compose @composeFiles ps app
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

$logs = docker compose @composeFiles logs app 2>&1
if ($logs -match "PostgreSQL unavailable") {
    Write-Error "app fell back to local SQLite - check DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT / DB_SSL_MODE in .env.prod."
    exit 1
}

$portLine = Select-String -Path ".env.prod" -Pattern "^APP_PORT=" | Select-Object -First 1
if ($portLine) {
    $port = $portLine.Line.Split("=")[1]
} else {
    $port = "8005"
}
Write-Host "Prod deployment is live on port $port (edge routes https://adjudication.acrncloud.com/ here)."
