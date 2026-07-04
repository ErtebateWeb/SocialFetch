#!/usr/bin/env bash
set -euo pipefail

echo "==> Running linters"
echo ""

echo "--- ruff check ---"
ruff check .

echo ""
echo "--- black --check ---"
black --check .

echo ""
echo "--- mypy ---"
mypy app/

echo ""
echo "==> All linters passed"
