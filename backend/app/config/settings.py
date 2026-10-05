"""Application settings (Pydantic Settings).

Settings are read from environment variables (and a local `.env` for development).
In AWS, secrets (API keys) are pulled from AWS Secrets Manager at startup — see
`app.config.secrets` — so they never live in Terraform, images or GitHub.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.secrets import load_secrets_into_environment

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(BACKEND_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # --- Runtime ---------------------------------------------------------------
    app_env: Literal["local", "dev", "prod", "test"] = "local"
    # "local": JSON-file repositories, local file storage, in-process worker.
    # "aws":   DynamoDB, S3, SQS, SES (optionally against LocalStack via AWS_ENDPOINT_URL).
    backend_mode: Literal["local", "aws"] = "local"
    auth_mode: Literal["local", "cognito"] = "local"
    log_level: str = "INFO"
    local_worker_enabled: bool = True

    # --- AWS -------------------------------------------------------------------
    aws_region: str = "eu-west-1"
    aws_endpoint_url: str | None = None
    dynamodb_table_prefix: str = "signalroom-dev"
    s3_bucket: str | None = None
    sqs_investigation_queue_url: str | None = None
    sqs_briefing_queue_url: str | None = None
    secrets_manager_secret_id: str | None = None

    # --- Cognito ---------------------------------------------------------------
    cognito_user_pool_id: str | None = None
    cognito_app_client_id: str | None = None
    cognito_region: str | None = None

    # --- Local auth (development only) ----------------------------------------
    local_jwt_secret: SecretStr = SecretStr("local-dev-only-change-me-please-32bytes!")
    local_token_ttl_minutes: int = 60 * 12

    # --- AI providers ----------------------------------------------------------
    # "auto" picks OpenRouter when its key exists, otherwise direct OpenAI/Gemini keys.
    ai_provider: Literal["auto", "openrouter", "direct"] = "auto"
    openrouter_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY")
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_api_key: SecretStr | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Model routing. Defaults are OpenRouter model IDs; when using direct providers
    # set e.g. OPENAI_MODEL=gpt-6-luna, GEMINI_MULTIMODAL_MODEL=gemini-3.8-flash.
    openai_model: str = "openai/gpt-6-luna"
    gemini_multimodal_model: str = "google/gemini-3.8-flash"
    gemini_transcribe_model: str = "google/gemini-3.8-flash"
    gemini_tts_model: str = "gemini-3.8-flash-tts"
    tts_model: str = "openai/gpt-audio-mini"
    tts_voice: str = "sage"
    image_model: str = "google/gemini-3.1-flash-image"
    # Multimodal embeddings (text + images in one vector space) for semantic search
    embedding_model: str = "google/gemini-embedding-2"
    ai_timeout_seconds: float = 120.0

    # --- Data providers ---------------------------------------------------------
    alphavantage_api_key: SecretStr | None = None
    fred_api_key: SecretStr | None = None
    sec_user_agent: str = "SignalRoom AI academic prototype (contact: signalroom-demo@example.com)"
    gdelt_enabled: bool = True
    gdelt_min_interval_seconds: float = 5.5

    # --- Email -----------------------------------------------------------------
    ses_from_email: str | None = None
    email_backend: Literal["auto", "ses", "local"] = "auto"

    # --- URLs / HTTP -----------------------------------------------------------
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    rate_limit_per_minute: int = 120

    # --- Product limits --------------------------------------------------------
    watchlist_max_size: int = 20
    # Budget protection for the public demo
    allowed_emails: str = ""  # comma-separated emails and/or @domains; empty = open
    max_investigations_per_day: int = 20  # per user (each includes several model calls)
    max_briefings_per_day: int = 5  # on-demand briefings per user
    max_document_mb: int = 25
    max_image_mb: int = 10
    max_audio_mb: int = 50
    max_video_mb: int = 40
    max_voice_command_mb: int = 4
    max_document_pages_for_vision: int = 4

    # --- Local storage ---------------------------------------------------------
    local_data_dir: Path = REPO_ROOT / "data" / "runtime"
    demo_data_dir: Path = REPO_ROOT / "demo_data"

    @model_validator(mode="after")
    def _validate_required(self) -> Settings:
        missing: list[str] = []
        if self.backend_mode == "aws":
            for name in ("s3_bucket", "sqs_investigation_queue_url", "sqs_briefing_queue_url"):
                if not getattr(self, name):
                    missing.append(name.upper())
        if self.auth_mode == "cognito":
            for name in ("cognito_user_pool_id", "cognito_app_client_id"):
                if not getattr(self, name):
                    missing.append(name.upper())
        if self.app_env in ("dev", "prod") and self.auth_mode == "local":
            missing.append("AUTH_MODE=cognito (local auth is not allowed outside local/test)")
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        return self

    # --- Derived helpers -------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_cognito_region(self) -> str:
        return self.cognito_region or self.aws_region

    @property
    def effective_email_backend(self) -> Literal["ses", "local"]:
        if self.email_backend == "auto":
            return "ses" if self.backend_mode == "aws" and self.ses_from_email else "local"
        return self.email_backend

    def secret(self, name: str) -> str | None:
        value = getattr(self, name, None)
        if isinstance(value, SecretStr):
            raw = value.get_secret_value().strip()
            return raw or None
        return None

    def provider_status(self) -> dict[str, bool]:
        """Which optional integrations are configured (never exposes values)."""
        return {
            "openrouter": self.secret("openrouter_api_key") is not None,
            "openai_direct": self.secret("openai_api_key") is not None,
            "gemini_direct": self.secret("gemini_api_key") is not None,
            "alpha_vantage": self.secret("alphavantage_api_key") is not None,
            "fred": self.secret("fred_api_key") is not None,
            "sec": bool(self.sec_user_agent),
            "gdelt": self.gdelt_enabled,
            "yahoo_finance": True,
            "ses": self.effective_email_backend == "ses",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_secrets_into_environment()
    return Settings()
