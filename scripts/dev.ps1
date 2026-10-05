# Windows local development: backend (FastAPI + in-process worker) + Vite frontend.
#   ./scripts/dev.ps1   -> http://localhost:5173   (API docs http://localhost:8000/api/docs)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not (Test-Path "$root/.env")) { Copy-Item "$root/.env.example" "$root/.env"; Write-Host "Created .env - add OPENROUTER_API_KEY" }

Push-Location "$root/backend"
if (-not (Test-Path ".venv")) {
  if (Get-Command uv -ErrorAction SilentlyContinue) { uv venv --python 3.12 .venv } else { python -m venv .venv }
}
if (Get-Command uv -ErrorAction SilentlyContinue) { uv pip install --python .venv/Scripts/python.exe -q -r requirements-dev.txt }
else { .venv/Scripts/python.exe -m pip install -q -r requirements-dev.txt }
$api = Start-Process -PassThru -NoNewWindow -FilePath ".venv/Scripts/python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"
Pop-Location

try {
  Push-Location "$root/frontend"
  if (-not (Test-Path "node_modules")) { npm ci }
  npx vite --port 5173
} finally {
  Pop-Location
  Stop-Process -Id $api.Id -ErrorAction SilentlyContinue
}
