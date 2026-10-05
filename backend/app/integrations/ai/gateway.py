"""AIGateway — the single entry point agents use to talk to models.

* Routes each *role* (reasoning, vision, transcription, tts, image) to a provider+model.
* Enforces structured output: every JSON answer is validated with Pydantic; on failure it
  retries once with a correction prompt, then raises (the caller degrades gracefully).
* Records model, provider, tokens, latency and cost for every call (UsageTracker).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from app.integrations.ai.audio_utils import pcm16_duration_seconds, pcm16_to_wav, silence
from app.integrations.ai.base import (
    AIError,
    AIResponseError,
    AIUnavailableError,
    AudioInput,
    ChatProvider,
    ChatRequest,
    ChatResult,
    EmbeddingInput,
    EmbeddingProvider,
    ImageGenerationProvider,
    ImageInput,
    ModelRole,
    SpeechProvider,
    UsageTracker,
    VideoInput,
)
from app.schemas.common import ModelUsage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class RoleBinding:
    provider: Any
    model: str


@dataclass
class SpeechOutput:
    wav: bytes
    duration_seconds: float


def extract_json(text: str) -> Any:
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def schema_instructions(schema: type[BaseModel]) -> str:
    compact = json.dumps(schema.model_json_schema(), separators=(",", ":"))
    return (
        "\n\nRespond with ONE JSON object only (no markdown, no prose) that validates against this "
        f"JSON Schema:\n{compact}"
    )


def split_for_speech(text: str, max_chars: int = 1100) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para) if len(para) > max_chars else [para]
        for sentence in sentences:
            if current and len(current) + len(sentence) + 2 > max_chars:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current}\n\n{sentence}" if current else sentence
    if current:
        chunks.append(current)
    return chunks


class AIGateway:
    def __init__(
        self,
        bindings: dict[ModelRole, RoleBinding],
        *,
        tts_voice: str = "sage",
        tracker: UsageTracker | None = None,
    ) -> None:
        self._bindings = bindings
        self._tts_voice = tts_voice
        self.tracker = tracker or UsageTracker()

    def with_tracker(self, tracker: UsageTracker) -> AIGateway:
        return AIGateway(self._bindings, tts_voice=self._tts_voice, tracker=tracker)

    # ------------------------------------------------------------------ introspection
    def available(self, role: ModelRole) -> bool:
        return role in self._bindings

    def model_for(self, role: ModelRole) -> str | None:
        binding = self._bindings.get(role)
        return binding.model if binding else None

    def describe(self) -> dict[str, dict[str, str]]:
        return {
            role: {"provider": getattr(b.provider, "name", "unknown"), "model": b.model}
            for role, b in self._bindings.items()
        }

    def _binding(self, role: ModelRole) -> RoleBinding:
        binding = self._bindings.get(role)
        if binding is None:
            raise AIUnavailableError(f"No AI provider configured for '{role}'")
        return binding

    def _record(
        self,
        result: ChatResult | None,
        *,
        provider: str,
        model: str,
        purpose: str,
        agent: str | None,
        latency_ms: int,
        ok: bool = True,
        cost: float | None = None,
    ) -> None:
        self.tracker.add(
            ModelUsage(
                provider=result.provider if result else provider,
                model=result.model if result else model,
                purpose=purpose,
                agent=agent,
                input_tokens=result.input_tokens if result else None,
                output_tokens=result.output_tokens if result else None,
                latency_ms=result.latency_ms if result else latency_ms,
                cost_usd=result.cost_usd if result else cost,
                ok=ok,
            )
        )

    # ------------------------------------------------------------------ chat
    async def _chat(
        self, role: ModelRole, request: ChatRequest, *, purpose: str, agent: str | None
    ) -> ChatResult:
        binding = self._binding(role)
        provider: ChatProvider = binding.provider
        request.model = binding.model
        try:
            result = await provider.chat(request)
        except AIError:
            self._record(
                None,
                provider=provider.name,
                model=binding.model,
                purpose=purpose,
                agent=agent,
                latency_ms=0,
                ok=False,
            )
            raise
        self._record(
            result,
            provider=provider.name,
            model=binding.model,
            purpose=purpose,
            agent=agent,
            latency_ms=result.latency_ms,
        )
        return result

    async def text(
        self,
        *,
        system: str,
        user: str,
        agent: str,
        purpose: str,
        role: ModelRole = "reasoning",
        max_tokens: int = 1500,
        temperature: float | None = 0.3,
    ) -> str:
        result = await self._chat(
            role,
            ChatRequest(system=system, user=user, model="", max_tokens=max_tokens, temperature=temperature),
            purpose=purpose,
            agent=agent,
        )
        if not result.text.strip():
            raise AIResponseError("Empty model response")
        return result.text.strip()

    async def structured(
        self,
        schema: type[T],
        *,
        system: str,
        user: str,
        agent: str,
        purpose: str,
        role: ModelRole = "reasoning",
        images: list[ImageInput] | None = None,
        audio: list[AudioInput] | None = None,
        videos: list[VideoInput] | None = None,
        max_tokens: int = 2500,
        temperature: float | None = 0.2,
    ) -> T:
        """Call a model and validate its JSON against `schema`. Retries once with a correction prompt."""
        full_system = system + schema_instructions(schema)
        request = ChatRequest(
            system=full_system,
            user=user,
            model="",
            json_mode=True,
            max_tokens=max_tokens,
            temperature=temperature,
            images=images or [],
            audio=audio or [],
            videos=videos or [],
        )
        result = await self._chat(role, request, purpose=purpose, agent=agent)
        try:
            return schema.model_validate(extract_json(result.text))
        except (json.JSONDecodeError, ValidationError, ValueError) as first_error:
            logger.warning(
                "structured_output_invalid_retrying",
                extra={"agent": agent, "purpose": purpose, "error_type": type(first_error).__name__},
            )
            correction = (
                f"{user}\n\nYour previous answer was not valid for the required schema "
                f"({_short_error(first_error)}). Previous answer:\n{result.text[:3000]}\n\n"
                "Return a corrected JSON object only."
            )
            retry_request = ChatRequest(
                system=full_system,
                user=correction,
                model="",
                json_mode=True,
                max_tokens=max_tokens,
                temperature=0.0,
                images=images or [],
                audio=audio or [],
                videos=videos or [],
            )
            retry = await self._chat(role, retry_request, purpose=f"{purpose}:retry", agent=agent)
            try:
                return schema.model_validate(extract_json(retry.text))
            except (json.JSONDecodeError, ValidationError, ValueError) as second_error:
                logger.error(
                    "structured_output_failed",
                    extra={"agent": agent, "purpose": purpose, "error_type": type(second_error).__name__},
                )
                raise AIResponseError(f"{agent}: model output failed validation twice") from second_error

    # ------------------------------------------------------------------ speech
    async def speech(
        self,
        text: str,
        *,
        agent: str = "voice",
        style: str = "calm, confident, analytical, measured pace, not sensationalist",
    ) -> SpeechOutput:
        binding = self._binding("tts")
        provider: SpeechProvider = binding.provider
        chunks = split_for_speech(text)
        pcm = bytearray()
        sample_rate = 24000
        for idx, chunk in enumerate(chunks):
            try:
                result = await provider.synthesize(
                    chunk, model=binding.model, voice=self._tts_voice, style=style
                )
            except AIError:
                self.tracker.add(
                    ModelUsage(
                        provider=provider.name,
                        model=binding.model,
                        purpose="tts",
                        agent=agent,
                        latency_ms=0,
                        ok=False,
                    )
                )
                raise
            sample_rate = result.sample_rate
            if idx:
                pcm.extend(silence(0.45, sample_rate))
            pcm.extend(result.pcm)
            self.tracker.add(
                ModelUsage(
                    provider=result.provider,
                    model=result.model,
                    purpose="tts",
                    agent=agent,
                    latency_ms=result.latency_ms,
                    cost_usd=result.cost_usd,
                    output_tokens=None,
                )
            )
        raw = bytes(pcm)
        return SpeechOutput(
            wav=pcm16_to_wav(raw, sample_rate),
            duration_seconds=round(pcm16_duration_seconds(raw, sample_rate), 1),
        )

    # ------------------------------------------------------------------ embeddings
    async def _embed(self, inputs: list[EmbeddingInput], *, agent: str, purpose: str) -> list[list[float]]:
        binding = self._binding("embedding")
        provider: EmbeddingProvider = binding.provider
        try:
            result = await provider.embed(inputs, model=binding.model)
        except AIError:
            self.tracker.add(
                ModelUsage(
                    provider=provider.name,
                    model=binding.model,
                    purpose=purpose,
                    agent=agent,
                    latency_ms=0,
                    ok=False,
                )
            )
            raise
        self.tracker.add(
            ModelUsage(
                provider=result.provider,
                model=result.model,
                purpose=purpose,
                agent=agent,
                input_tokens=result.input_tokens,
                latency_ms=result.latency_ms,
                cost_usd=result.cost_usd,
            )
        )
        return result.vectors

    async def embed_texts(
        self, texts: list[str], *, agent: str = "search", batch_size: int = 64
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = [EmbeddingInput(text=t[:6000]) for t in texts[i : i + batch_size]]
            vectors.extend(await self._embed(chunk, agent=agent, purpose="embedding_text"))
        return vectors

    async def embed_image(self, data: bytes, mime_type: str, *, agent: str = "search") -> list[float]:
        return (
            await self._embed(
                [EmbeddingInput(image=data, mime_type=mime_type)], agent=agent, purpose="embedding_image"
            )
        )[0]

    # ------------------------------------------------------------------ image generation
    async def image(self, prompt: str, *, agent: str = "infographic") -> tuple[bytes, str]:
        binding = self._binding("image")
        provider: ImageGenerationProvider = binding.provider
        result = await provider.generate_image(prompt, model=binding.model)
        self.tracker.add(
            ModelUsage(
                provider=result.provider,
                model=result.model,
                purpose="image_generation",
                agent=agent,
                latency_ms=result.latency_ms,
                cost_usd=result.cost_usd,
            )
        )
        return result.data, result.mime_type


def _short_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        errs = exc.errors()[:3]
        return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errs)
    return type(exc).__name__


def build_gateway(
    *,
    openrouter_key: str | None,
    openai_key: str | None,
    gemini_key: str | None,
    mode: Literal["auto", "openrouter", "direct"],
    models: dict[str, str],
    openrouter_base_url: str,
    openai_base_url: str,
    gemini_base_url: str,
    app_url: str,
    timeout: float,
    tts_voice: str,
) -> AIGateway:
    """Create the gateway from configuration. Missing keys simply leave roles unbound."""
    from app.integrations.ai.gemini import GeminiProvider
    from app.integrations.ai.openai import OpenAIProvider
    from app.integrations.ai.openrouter import OpenRouterProvider

    bindings: dict[ModelRole, RoleBinding] = {}
    voice = tts_voice
    if openrouter_key and mode in ("auto", "openrouter"):
        router = OpenRouterProvider(
            api_key=openrouter_key, base_url=openrouter_base_url, app_url=app_url, timeout=timeout
        )
        bindings["reasoning"] = RoleBinding(router, models["reasoning"])
        bindings["vision"] = RoleBinding(router, models["vision"])
        bindings["transcription"] = RoleBinding(router, models["transcription"])
        bindings["tts"] = RoleBinding(router, models["tts"])
        bindings["image"] = RoleBinding(router, models["image"])
        if models.get("embedding"):
            bindings["embedding"] = RoleBinding(router, models["embedding"])
    else:
        if openai_key:
            direct_openai = OpenAIProvider(api_key=openai_key, base_url=openai_base_url, timeout=timeout)
            bindings["reasoning"] = RoleBinding(direct_openai, models["reasoning"].split("/", 1)[-1])
            bindings["embedding"] = RoleBinding(direct_openai, "text-embedding-3-small")  # text-only fallback
        if gemini_key:
            gemini = GeminiProvider(api_key=gemini_key, base_url=gemini_base_url, timeout=timeout)
            bindings["vision"] = RoleBinding(gemini, models["vision"].split("/", 1)[-1])
            bindings["transcription"] = RoleBinding(gemini, models["transcription"].split("/", 1)[-1])
            bindings["tts"] = RoleBinding(gemini, models["gemini_tts"])
            voice = "Charon"
            if "reasoning" not in bindings:
                bindings["reasoning"] = RoleBinding(gemini, models["vision"].split("/", 1)[-1])
    return AIGateway(bindings, tts_voice=voice)
