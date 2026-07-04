#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Running tests" -ForegroundColor Cyan
Write-Host ""

if ($args -contains "--coverage") {
    pytest --cov --cov-report=term-missing --cov-report=html
} else {
    pytest @args
}
