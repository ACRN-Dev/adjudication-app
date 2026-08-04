<#
PowerShell helper to activate the project's virtual environment.
Usage:
  .\scripts\activate_venv.ps1    # run in PowerShell (will activate in current session)

This script sets a temporary ExecutionPolicy bypass and sources the venv Activate.ps1.
#>
param()

$venvActivate = Join-Path -Path $PSScriptRoot -ChildPath "..\venv\Scripts\Activate.ps1"
$venvActivate = [System.IO.Path]::GetFullPath($venvActivate)

if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment activation script not found at: $venvActivate"
    exit 1
}

# Allow this process to run unsigned scripts, then dot-source the Activate.ps1 so it affects current session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. $venvActivate
Write-Host "Activated virtual environment from: $venvActivate" -ForegroundColor Green
