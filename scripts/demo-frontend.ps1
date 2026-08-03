<#
.SYNOPSIS
    Starts the HYDRA frontend dev server wired to the local backend replay demo.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location "$repoRoot\frontend"

$env:VITE_HYDRA_REPLAY_DEMO = "true"
$env:VITE_API_BASE = "http://127.0.0.1:8000/api"

Write-Host "==> Starting frontend dev server (VITE_HYDRA_REPLAY_DEMO=true, VITE_API_BASE=$env:VITE_API_BASE)" -ForegroundColor Cyan
npm run dev
