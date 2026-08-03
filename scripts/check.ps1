<#
.SYNOPSIS
    Runs the standard HYDRA validation suite: backend compile checks, layer1
    pytest suite, and frontend build. Run before showing a diff or committing.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "==> Activating .venv" -ForegroundColor Cyan
& "$repoRoot\.venv\Scripts\Activate.ps1"

Write-Host "==> Compiling backend/api.py" -ForegroundColor Cyan
python -m py_compile backend/api.py
if ($LASTEXITCODE -ne 0) { throw "py_compile failed: backend/api.py" }

Write-Host "==> Compiling main.py" -ForegroundColor Cyan
python -m py_compile main.py
if ($LASTEXITCODE -ne 0) { throw "py_compile failed: main.py" }

Write-Host "==> Compiling backend/models.py" -ForegroundColor Cyan
python -m py_compile backend/models.py
if ($LASTEXITCODE -ne 0) { throw "py_compile failed: backend/models.py" }

Write-Host "==> Compiling stream_engine/drift_engine.py" -ForegroundColor Cyan
python -m py_compile stream_engine/drift_engine.py
if ($LASTEXITCODE -ne 0) { throw "py_compile failed: stream_engine/drift_engine.py" }

Write-Host "==> Running tests/test_layer1_pipeline.py" -ForegroundColor Cyan
python -m pytest tests/test_layer1_pipeline.py -q
if ($LASTEXITCODE -ne 0) { throw "pytest failed: tests/test_layer1_pipeline.py" }

Write-Host "==> Building frontend" -ForegroundColor Cyan
Set-Location "$repoRoot\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }

Set-Location $repoRoot

Write-Host "==> git status --short" -ForegroundColor Cyan
git status --short

Write-Host "==> All checks passed" -ForegroundColor Green
