#!/usr/bin/env bash
set -euo pipefail

echo "==> Running tests"
echo ""

if [ "${1:-}" = "--coverage" ]; then
    pytest --cov --cov-report=term-missing --cov-report=html
else
    pytest "$@"
fi
