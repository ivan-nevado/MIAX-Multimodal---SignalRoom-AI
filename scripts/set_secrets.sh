#!/usr/bin/env bash
# Populate the AWS Secrets Manager secret created by Terraform with the API keys from
# your local .env. Values are never printed, never passed through Terraform state and
# never stored in GitHub. Requires: aws CLI (logged in), terraform, python.
#
#   ./scripts/set_secrets.sh               # uses terraform output secret_name
#   SECRET_ID=signalroom/dev/app ./scripts/set_secrets.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
TF_DIR="$ROOT/terraform/environments/dev"

[ -f "$ENV_FILE" ] || { echo "Missing $ENV_FILE (copy .env.example)"; exit 1; }
SECRET_ID="${SECRET_ID:-$(terraform -chdir="$TF_DIR" output -raw secret_name)}"
REGION="${AWS_REGION:-$(terraform -chdir="$TF_DIR" output -raw region 2>/dev/null || echo eu-west-1)}"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
python - "$ENV_FILE" "$TMP" <<'PY'
import json, sys
env = {}
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.split(" #")[0].strip().strip('"').strip("'")
secret = {
    "OPENROUTER_API_KEY": env.get("OPENROUTER_API_KEY") or env.get("OPEN_ROUTER_API_KEY", ""),
    "OPENAI_API_KEY": env.get("OPENAI_API_KEY", ""),
    "GEMINI_API_KEY": env.get("GEMINI_API_KEY", ""),
    "ALPHAVANTAGE_API_KEY": env.get("ALPHAVANTAGE_API_KEY", ""),
    "FRED_API_KEY": env.get("FRED_API_KEY", ""),
    "SEC_USER_AGENT": env.get("SEC_USER_AGENT", "SignalRoom AI academic prototype (contact: signalroom-demo@example.com)"),
    "SES_FROM_EMAIL": env.get("SES_FROM_EMAIL", ""),
}
if not (secret["OPENROUTER_API_KEY"] or secret["OPENAI_API_KEY"] or secret["GEMINI_API_KEY"]):
    sys.exit("No AI key found in .env (OPENROUTER_API_KEY)")
json.dump(secret, open(sys.argv[2], "w"))
print("Prepared keys:", ", ".join(k for k, v in secret.items() if v))
PY

aws secretsmanager put-secret-value --region "$REGION" --secret-id "$SECRET_ID" --secret-string "file://$TMP" >/dev/null
echo "Secret '$SECRET_ID' updated. Restart tasks to load it: ./scripts/deploy.sh --restart-only"
