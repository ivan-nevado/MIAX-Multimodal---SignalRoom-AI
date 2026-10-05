"""Runtime secret retrieval from AWS Secrets Manager.

The deployed ECS tasks receive only the *name/ARN* of the secret
(`SECRETS_MANAGER_SECRET_ID`). At process start we fetch the JSON secret
value once and expose its keys as environment variables so Pydantic Settings
can read them. Values already present in the environment win, which keeps
local development (`.env`) and tests simple.

The secret is a JSON object such as::

    {"OPENROUTER_API_KEY": "...", "ALPHAVANTAGE_API_KEY": "", "FRED_API_KEY": "",
     "SEC_USER_AGENT": "...", "SES_FROM_EMAIL": "..."}
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

ALLOWED_SECRET_KEYS = frozenset(
    {
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ALPHAVANTAGE_API_KEY",
        "FRED_API_KEY",
        "SEC_USER_AGENT",
        "SES_FROM_EMAIL",
        "LOCAL_JWT_SECRET",
    }
)


def fetch_secret_values(secret_id: str, region: str, endpoint_url: str | None = None) -> dict[str, str]:
    import boto3  # imported lazily: local development does not need AWS

    client = boto3.client("secretsmanager", region_name=region, endpoint_url=endpoint_url)
    response = client.get_secret_value(SecretId=secret_id)
    raw = response.get("SecretString") or "{}"
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Secrets Manager value must be a JSON object")
    return {str(k): str(v) for k, v in data.items() if v is not None}


def load_secrets_into_environment() -> list[str]:
    """Populate os.environ from Secrets Manager. Returns the key names loaded (never values)."""
    secret_id = os.environ.get("SECRETS_MANAGER_SECRET_ID")
    if not secret_id:
        return []
    region = os.environ.get("AWS_REGION", "eu-west-1")
    endpoint = os.environ.get("AWS_ENDPOINT_URL") or None
    try:
        values = fetch_secret_values(secret_id, region, endpoint)
    except Exception as exc:  # pragma: no cover - exercised in AWS only
        # Do not crash: optional providers degrade gracefully, and the health
        # endpoint reports which providers are configured.
        logger.error("secrets_manager_load_failed", extra={"error_type": type(exc).__name__})
        return []
    loaded: list[str] = []
    for key, value in values.items():
        if key not in ALLOWED_SECRET_KEYS or not value.strip():
            continue
        if os.environ.get(key):
            continue
        os.environ[key] = value
        loaded.append(key)
    logger.info("secrets_manager_loaded", extra={"keys": sorted(loaded)})
    return loaded
