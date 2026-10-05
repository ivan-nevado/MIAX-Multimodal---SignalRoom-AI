# The secret CONTAINER only. Terraform never sees the values (they would end up in
# state). Populate it with scripts/set_secrets.sh / set_secrets.ps1, which reads your
# local .env and calls `aws secretsmanager put-secret-value`.
#
# The ECS tasks receive only SECRETS_MANAGER_SECRET_ID and load the JSON value at
# startup (backend/app/config/secrets.py).

resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.name}/app"
  description             = "SignalRoom application API keys (JSON: OPENROUTER_API_KEY, ALPHAVANTAGE_API_KEY, FRED_API_KEY, SEC_USER_AGENT, SES_FROM_EMAIL)"
  recovery_window_in_days = var.recovery_window_in_days
}
