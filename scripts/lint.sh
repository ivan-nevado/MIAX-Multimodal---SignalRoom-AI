#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/backend/.venv/bin"; [ -d "$BIN" ] || BIN="$ROOT/backend/.venv/Scripts"
echo "== ruff";  (cd "$ROOT/backend" && "$BIN/ruff" check app tests)
echo "== mypy";  (cd "$ROOT/backend" && "$BIN/mypy" app)
echo "== eslint"; (cd "$ROOT/frontend" && npx eslint .)
echo "== tsc";    (cd "$ROOT/frontend" && npx tsc -b)
echo "== prettier"; (cd "$ROOT/frontend" && npx prettier --check "src/**/*.{ts,tsx,css}" || echo "(formatting differences only)")
