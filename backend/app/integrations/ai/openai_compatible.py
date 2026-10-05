"""Client for OpenAI-compatible Chat Completions APIs (OpenAI, OpenRouter)."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any

import httpx

from app.integrations.ai.audio_utils import audio_format_for_mime
from app.integrations.ai.base import (
    AIError,
    AIResponseError,
    ChatRequest,
    ChatResult,
    EmbeddingInput,
    EmbeddingResult,
    ImageResult,
    SpeechResult,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class OpenAICompatibleClient:
    name = "openai-compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float = 120.0,
        extra_headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._extra_headers = extra_headers or {}
        self._transport = transport
        self._max_retries = max_retries

    # ------------------------------------------------------------------ helpers
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with self._client() as client:
                    resp = await client.post(url, headers=self._headers(), json=payload)
                if resp.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                    await asyncio.sleep(1.5 * (2**attempt))
                    continue
                if resp.status_code >= 400:
                    raise AIError(f"{self.name} HTTP {resp.status_code}: {_safe_error(resp)}")
                data: dict[str, Any] = resp.json()
                if "error" in data and not data.get("choices"):
                    raise AIError(f"{self.name} error: {str(data['error'])[:300]}")
                return data
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(1.5 * (2**attempt))
                    continue
        raise AIError(f"{self.name} request failed: {type(last_error).__name__}")

    @staticmethod
    def _user_content(request: ChatRequest) -> str | list[dict[str, Any]]:
        if not request.images and not request.audio and not request.videos:
            return request.user
        parts: list[dict[str, Any]] = [{"type": "text", "text": request.user}]
        for img in request.images:
            b64 = base64.b64encode(img.data).decode("ascii")
            parts.append({"type": "image_url", "image_url": {"url": f"data:{img.mime_type};base64,{b64}"}})
        for aud in request.audio:
            parts.append(
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64.b64encode(aud.data).decode("ascii"),
                        "format": audio_format_for_mime(aud.mime_type),
                    },
                }
            )
        for vid in request.videos:
            b64 = base64.b64encode(vid.data).decode("ascii")
            parts.append({"type": "video_url", "video_url": {"url": f"data:{vid.mime_type};base64,{b64}"}})
        return parts

    def _chat_payload(self, request: ChatRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": self._user_content(request)},
            ],
            "max_tokens": request.max_tokens,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    # ------------------------------------------------------------------ chat
    async def chat(self, request: ChatRequest) -> ChatResult:
        started = time.perf_counter()
        data = await self._post("/chat/completions", self._chat_payload(request))
        latency = int((time.perf_counter() - started) * 1000)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError(f"{self.name}: malformed response") from exc
        text = message.get("content") or ""
        if isinstance(text, list):  # some providers return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        usage = data.get("usage") or {}
        return ChatResult(
            text=str(text),
            model=str(data.get("model") or request.model),
            provider=str(data.get("provider") or self.name),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            cost_usd=usage.get("cost"),
            latency_ms=latency,
            raw=None,
        )

    # ------------------------------------------------------------------ speech (chat audio output)
    async def synthesize(self, text: str, *, model: str, voice: str, style: str) -> SpeechResult:
        """Text-to-speech through an audio-output chat model (streams PCM16 @ 24 kHz)."""
        payload = {
            "model": model,
            "modalities": ["text", "audio"],
            "audio": {"voice": voice, "format": "pcm16"},
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a text-to-speech narrator. Read the user's text aloud VERBATIM, "
                        "without adding, removing or commenting on anything. Delivery style: " + style
                    ),
                },
                {"role": "user", "content": text},
            ],
        }
        started = time.perf_counter()
        pcm = bytearray()
        cost: float | None = None
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            pcm.clear()
            try:
                async with (
                    self._client() as client,
                    client.stream(
                        "POST", f"{self._base_url}/chat/completions", headers=self._headers(), json=payload
                    ) as resp,
                ):
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "ignore")[:300]
                        if resp.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                            await asyncio.sleep(1.5 * (2**attempt))
                            continue
                        raise AIError(f"{self.name} TTS HTTP {resp.status_code}: {body}")
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if chunk == "[DONE]":
                            break
                        try:
                            event = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        usage = event.get("usage")
                        if usage and usage.get("cost") is not None:
                            cost = usage.get("cost")
                        for choice in event.get("choices") or []:
                            audio = (choice.get("delta") or {}).get("audio") or {}
                            if audio.get("data"):
                                pcm.extend(base64.b64decode(audio["data"]))
                break
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(1.5 * (2**attempt))
                    continue
                raise AIError(f"{self.name} TTS failed: {type(exc).__name__}") from exc
        if not pcm:
            raise AIResponseError(
                f"{self.name} TTS returned no audio ({type(last_error).__name__ if last_error else 'empty'})"
            )
        return SpeechResult(
            pcm=bytes(pcm),
            sample_rate=24000,
            model=model,
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=cost,
        )

    # ------------------------------------------------------------------ embeddings
    async def embed(self, inputs: list[EmbeddingInput], *, model: str) -> EmbeddingResult:
        """Text and/or image embeddings. Images use the multimodal content format."""
        payload_inputs: list[Any] = []
        for item in inputs:
            if item.image is not None:
                b64 = base64.b64encode(item.image).decode("ascii")
                payload_inputs.append(
                    {
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{item.mime_type};base64,{b64}"}}
                        ]
                    }
                )
            else:
                payload_inputs.append(item.text or "")
        started = time.perf_counter()
        data = await self._post("/embeddings", {"model": model, "input": payload_inputs})
        try:
            rows = sorted(data["data"], key=lambda r: r.get("index", 0))
            vectors = [list(map(float, r["embedding"])) for r in rows]
        except (KeyError, TypeError) as exc:
            raise AIResponseError(f"{self.name}: malformed embeddings response") from exc
        if len(vectors) != len(inputs):
            raise AIResponseError(f"{self.name}: embeddings count mismatch")
        usage = data.get("usage") or {}
        return EmbeddingResult(
            vectors=vectors,
            model=str(data.get("model") or model),
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=usage.get("prompt_tokens"),
            cost_usd=usage.get("cost"),
        )

    # ------------------------------------------------------------------ image generation
    async def generate_image(self, prompt: str, *, model: str) -> ImageResult:
        started = time.perf_counter()
        data = await self._post(
            "/chat/completions",
            {
                "model": model,
                "modalities": ["image", "text"],
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        try:
            message = data["choices"][0]["message"]
            images = message.get("images") or []
            url = images[0]["image_url"]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError(f"{self.name}: no image returned") from exc
        if not url.startswith("data:"):
            raise AIResponseError(f"{self.name}: unexpected image URL format")
        header, b64 = url.split(",", 1)
        mime = header[5:].split(";")[0] or "image/png"
        usage = data.get("usage") or {}
        return ImageResult(
            data=base64.b64decode(b64),
            mime_type=mime,
            model=model,
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=usage.get("cost"),
        )


def _safe_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error", data)
        if isinstance(err, dict):
            return str(err.get("message", err))[:300]
        return str(err)[:300]
    except ValueError:
        return resp.text[:300]
