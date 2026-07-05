#!/usr/bin/env bash
set -euo pipefail

echo "==> SocialFetch Bootstrap"
echo ""

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" &>/dev/null; then
    echo "Error: $PYTHON not found. Install Python 3.11+ first."
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1)
echo "Using: $PYTHON_VERSION"

echo ""
echo "1/4 Creating virtual environment..."
$PYTHON -m venv .venv

echo "2/4 Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "3/4 Installing package in editable mode with dev dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

echo "4/4 Installing pre-commit hooks..."
pre-commit install

echo ""
echo "==> Bootstrap complete!"
echo "    Activate the environment: source .venv/bin/activate"
echo "    Run tests:                ./scripts/test.sh"
echo "    Run linters:              ./scripts/lint.sh"
