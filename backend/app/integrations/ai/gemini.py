"""Native Google Gemini adapter (generateContent REST API).

Used when GEMINI_API_KEY is configured directly (instead of OpenRouter). It covers
multimodal understanding (images, PDF pages, audio transcription) and native
Gemini TTS (`responseModalities: ["AUDIO"]`, PCM16 @ 24 kHz).
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx

from app.integrations.ai.base import AIError, AIResponseError, ChatRequest, ChatResult, SpeechResult

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Gemini prebuilt voice with a calm, firm delivery suited to a financial briefing.
DEFAULT_GEMINI_VOICE = "Charon"


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport
        self._max_retries = max_retries

    async def _generate(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        model_id = model.split("/", 1)[-1]  # accept "google/gemini-..." style IDs too
        url = f"{self._base_url}/models/{model_id}:generateContent"
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                    resp = await client.post(url, headers={"x-goog-api-key": self._api_key}, json=body)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self._max_retries:
                    await asyncio.sleep(1.5 * (2**attempt))
                    continue
                raise AIError(f"gemini request failed: {type(exc).__name__}") from exc
            if resp.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                await asyncio.sleep(1.5 * (2**attempt))
                continue
            if resp.status_code >= 400:
                raise AIError(f"gemini HTTP {resp.status_code}")
            data: dict[str, Any] = resp.json()
            return data
        raise AIError("gemini request failed")

    async def chat(self, request: ChatRequest) -> ChatResult:
        parts: list[dict[str, Any]] = [{"text": request.user}]
        for img in request.images:
            parts.append(
                {"inline_data": {"mime_type": img.mime_type, "data": base64.b64encode(img.data).decode()}}
            )
        for aud in request.audio:
            parts.append(
                {"inline_data": {"mime_type": aud.mime_type, "data": base64.b64encode(aud.data).decode()}}
            )
        for vid in request.videos:
            parts.append(
                {"inline_data": {"mime_type": vid.mime_type, "data": base64.b64encode(vid.data).decode()}}
            )
        generation: dict[str, Any] = {"maxOutputTokens": request.max_tokens}
        if request.temperature is not None:
            generation["temperature"] = request.temperature
        if request.json_mode:
            generation["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation,
        }
        started = time.perf_counter()
        data = await self._generate(request.model, body)
        try:
            cand_parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in cand_parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("gemini: malformed response") from exc
        usage = data.get("usageMetadata") or {}
        return ChatResult(
            text=text,
            model=request.model,
            provider=self.name,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def synthesize(self, text: str, *, model: str, voice: str, style: str) -> SpeechResult:
        body = {
            "contents": [{"role": "user", "parts": [{"text": f"{style}\n\n{text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice or DEFAULT_GEMINI_VOICE}}
                },
            },
        }
        started = time.perf_counter()
        data = await self._generate(model, body)
        try:
            inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            pcm = base64.b64decode(inline["data"])
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("gemini TTS: no audio returned") from exc
        return SpeechResult(
            pcm=pcm,
            sample_rate=24000,
            model=model,
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
