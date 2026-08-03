<#
.SYNOPSIS
    Starts the HYDRA backend dev server (uvicorn, auto-reload) on port 8000.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "==> Activating .venv" -ForegroundColor Cyan
& "$repoRoot\.venv\Scripts\Activate.ps1"

Write-Host "==> Starting backend on http://127.0.0.1:8000" -ForegroundColor Cyan
python -m uvicorn backend.api:app --reload --port 8000
