"""Provider-neutral AI interfaces. Agents never import provider SDKs or HTTP clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.schemas.common import ModelUsage

ModelRole = Literal["reasoning", "vision", "transcription", "tts", "image", "embedding"]


class AIError(Exception):
    """Base error for AI provider failures (safe to show a generic message to users)."""


class AIUnavailableError(AIError):
    """No provider is configured for the requested capability."""


class AIResponseError(AIError):
    """The provider answered but the payload was unusable."""


@dataclass
class ImageInput:
    data: bytes
    mime_type: str


@dataclass
class AudioInput:
    data: bytes
    mime_type: str


@dataclass
class VideoInput:
    data: bytes
    mime_type: str


@dataclass
class EmbeddingInput:
    """Either text or an image (multimodal embedding models place both in one vector space)."""

    text: str | None = None
    image: bytes | None = None
    mime_type: str = "image/png"


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    provider: str
    latency_ms: int
    input_tokens: int | None = None
    cost_usd: float | None = None


@dataclass
class ChatRequest:
    system: str
    user: str
    model: str
    json_mode: bool = False
    max_tokens: int = 2000
    temperature: float | None = 0.2
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    images: list[ImageInput] = field(default_factory=list)
    audio: list[AudioInput] = field(default_factory=list)
    videos: list[VideoInput] = field(default_factory=list)


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    latency_ms: int = 0
    raw: dict[str, Any] | None = None


@dataclass
class SpeechResult:
    pcm: bytes
    sample_rate: int
    model: str
    provider: str
    latency_ms: int
    cost_usd: float | None = None


@dataclass
class ImageResult:
    data: bytes
    mime_type: str
    model: str
    provider: str
    latency_ms: int
    cost_usd: float | None = None


class ChatProvider(Protocol):
    name: str

    async def chat(self, request: ChatRequest) -> ChatResult: ...


class SpeechProvider(Protocol):
    name: str

    async def synthesize(self, text: str, *, model: str, voice: str, style: str) -> SpeechResult: ...


class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, inputs: list[EmbeddingInput], *, model: str) -> EmbeddingResult: ...


class ImageGenerationProvider(Protocol):
    name: str

    async def generate_image(self, prompt: str, *, model: str) -> ImageResult: ...


class UsageTracker:
    """Collects per-investigation model usage (model, provider, tokens, latency, cost)."""

    def __init__(self) -> None:
        self.records: list[ModelUsage] = []

    def add(self, usage: ModelUsage) -> None:
        self.records.append(usage)

    @property
    def total_cost(self) -> float:
        return round(sum(r.cost_usd or 0.0 for r in self.records), 6)
