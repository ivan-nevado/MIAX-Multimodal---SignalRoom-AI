"""OpenRouter adapter — one key, many specialised models (OpenAI, Google, ...).

OpenRouter exposes the OpenAI Chat Completions contract, including image/audio
inputs, audio output (TTS through `openai/gpt-audio-mini`) and image output.
"""

from __future__ import annotations

import httpx

from app.integrations.ai.openai_compatible import OpenAICompatibleClient


class OpenRouterProvider(OpenAICompatibleClient):
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_url: str = "https://github.com/signalroom-ai",
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            extra_headers={"HTTP-Referer": app_url, "X-Title": "SignalRoom AI"},
        )
