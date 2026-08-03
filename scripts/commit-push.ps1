<#
.SYNOPSIS
    Commits and pushes with a safe default: only stages already-tracked,
    modified files. Untracked files are never added unless -IncludeUntracked
    is passed explicitly.

.PARAMETER Message
    Commit message. Required.

.PARAMETER IncludeUntracked
    If set, also stages new (untracked) files. Off by default.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/commit-push.ps1 -Message "fix: whatever"

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/commit-push.ps1 -Message "feat: whatever" -IncludeUntracked
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$IncludeUntracked
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "==> git status (before)" -ForegroundColor Cyan
git status

if ($IncludeUntracked) {
    Write-Host "==> Staging all changes, including untracked files (-IncludeUntracked)" -ForegroundColor Yellow
    git add -A
}
else {
    Write-Host "==> Staging only tracked, modified files" -ForegroundColor Cyan
    $modified = git diff --name-only
    $modified += git diff --name-only --cached
    $modified = $modified | Where-Object { $_ } | Select-Object -Unique

    if (-not $modified) {
        Write-Host "No tracked modified files to stage. Use -IncludeUntracked to add new files." -ForegroundColor Yellow
        exit 0
    }

    foreach ($file in $modified) {
        git add -- $file
    }
}

Write-Host "==> git commit" -ForegroundColor Cyan
git commit -m $Message
if ($LASTEXITCODE -ne 0) { throw "git commit failed" }

Write-Host "==> git push" -ForegroundColor Cyan
git push
if ($LASTEXITCODE -ne 0) { throw "git push failed" }

Write-Host "==> git status (after)" -ForegroundColor Cyan
git status
