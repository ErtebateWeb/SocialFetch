#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> SocialFetch Bootstrap" -ForegroundColor Cyan
Write-Host ""

$Python = "py -3.11"

try {
    $Version = & $Python --version 2>&1
    Write-Host "Using: $Version"
} catch {
    Write-Host "Error: Python 3.11 not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "1/4 Creating virtual environment..." -ForegroundColor Yellow
& $Python -m venv .venv

Write-Host "2/4 Activating virtual environment..." -ForegroundColor Yellow
& .venv\Scripts\Activate.ps1

Write-Host "3/4 Installing package in editable mode with dev dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -e ".[dev]"

Write-Host "4/4 Installing pre-commit hooks..." -ForegroundColor Yellow
pre-commit install

Write-Host ""
Write-Host "==> Bootstrap complete!" -ForegroundColor Green
Write-Host "    Activate the environment: .venv\Scripts\Activate.ps1"
Write-Host "    Run tests:                .\scripts\test.ps1"
Write-Host "    Run linters:              .\scripts\lint.ps1"
