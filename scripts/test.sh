#!/usr/bin/env bash
# Offline test suites (no paid APIs, no AWS). Add --live to also run the live OpenRouter/market tests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -f "$PY" ] || PY="$ROOT/backend/.venv/Scripts/python.exe"
echo "== backend: pytest"; (cd "$ROOT/backend" && "$PY" -m pytest -q)
if [ "${1:-}" = "--live" ]; then echo "== backend: live"; (cd "$ROOT/backend" && RUN_LIVE_TESTS=1 "$PY" -m pytest -m live -q); fi
echo "== frontend: vitest"; (cd "$ROOT/frontend" && npx vitest run)
echo "== terraform: fmt + validate (no AWS calls)"
terraform -chdir="$ROOT/terraform" fmt -check -recursive
terraform -chdir="$ROOT/terraform/environments/dev" init -backend=false -input=false >/dev/null
terraform -chdir="$ROOT/terraform/environments/dev" validate
