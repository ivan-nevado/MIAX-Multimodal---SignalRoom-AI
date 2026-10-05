# Local development

## Requirements
Python 3.11+ (3.12 recommended; `uv` optional), Node 20+, optional Docker.

## 1. Configure
```bash
cp .env.example .env      # add OPENROUTER_API_KEY (one key for every model)
```
Without a key the app still runs: deterministic metrics, charts and evidence scoring work and the UI states that
the AI narrative is unavailable.

## 2. Run

| Option | Command | URLs |
|---|---|---|
| Scripts (macOS/Linux/Git Bash) | `./scripts/dev.sh` | UI http://localhost:5173 · API docs http://localhost:8000/api/docs |
| PowerShell | `./scripts/dev.ps1` | same |
| Docker | `docker compose up --build` | UI http://localhost:8080 · API http://localhost:8000 |
| AWS code paths on LocalStack | `docker compose --profile aws-local up --build` | UI http://localhost:8081 · API http://localhost:8001 |
| Frontend-only demo (no backend, no keys) | `cd frontend && VITE_DEMO_MODE=true npx vite` | http://localhost:5173 |

`BACKEND_MODE=local` stores data in `data/runtime/` (JSON files + local file storage with HMAC-signed
"presigned" URLs) and runs the queue worker in a background thread. `AUTH_MODE=local` issues development JWTs.

Demo account with recorded real runs: `./scripts/seed_demo.sh` → `demo@signalroom.ai` / `DemoPassw0rd`.

## 3. Test & lint
```bash
./scripts/test.sh          # backend pytest (mocked providers + moto), frontend vitest, terraform validate
./scripts/test.sh --live   # + live tests (real OpenRouter, Yahoo, SEC, GDELT) — a few cents
./scripts/lint.sh          # ruff, mypy, eslint, tsc, prettier
python scripts/e2e_screenshots.py   # Playwright E2E through the real UI (needs both servers + Chrome)
```

## 4. Demo assets
```bash
python scripts/generate_demo_assets.py   # synthetic PDF (fictional company) + chart from real Yahoo data
python scripts/generate_demo_audio.py    # synthetic multi-voice earnings call via TTS
python scripts/record_demo_data.py       # record real runs for VITE_DEMO_MODE (costs ~$0.15)
```
