#!/usr/bin/env bash
# Create a ready-to-use demo account in the LOCAL backend with the recorded (real) runs:
#   email: demo@signalroom.ai   password: DemoPassw0rd
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -f "$PY" ] || PY="$ROOT/backend/.venv/Scripts/python.exe"
"$PY" "$ROOT/scripts/seed_demo.py"
