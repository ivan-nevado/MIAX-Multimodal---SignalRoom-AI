#!/usr/bin/env bash
# Local development without Docker: backend (FastAPI + in-process worker) + Vite frontend.
#   ./scripts/dev.sh            -> http://localhost:5173  (API docs: http://localhost:8000/api/docs)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] || { cp "$ROOT/.env.example" "$ROOT/.env"; echo "Created .env from .env.example - add OPENROUTER_API_KEY"; }

cd "$ROOT/backend"
if [ ! -d .venv ]; then
  if command -v uv >/dev/null; then uv venv --python 3.12 .venv; else python3 -m venv .venv; fi
fi
PY=".venv/bin/python"; [ -f "$PY" ] || PY=".venv/Scripts/python.exe"
if command -v uv >/dev/null; then uv pip install --python "$PY" -q -r requirements-dev.txt; else "$PY" -m pip install -q -r requirements-dev.txt; fi
"$PY" -m uvicorn app.main:app --reload --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

cd "$ROOT/frontend"
[ -d node_modules ] || npm ci
npx vite --port 5173
