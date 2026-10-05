"""Direct OpenAI adapter (used when OPENAI_API_KEY is configured and OpenRouter is not)."""

from __future__ import annotations

import httpx

from app.integrations.ai.openai_compatible import OpenAICompatibleClient


class OpenAIProvider(OpenAICompatibleClient):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout, transport=transport)
