#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Running linters" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- ruff check ---" -ForegroundColor Yellow
ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "--- black --check ---" -ForegroundColor Yellow
black --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "--- mypy ---" -ForegroundColor Yellow
mypy socialfetch/
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> All linters passed" -ForegroundColor Green
