from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal[
    "news",
    "market_data",
    "sec_filing",
    "financial_data",
    "macro",
    "document",
    "image",
    "audio",
    "video",
]

EvidenceConfidence = Literal["high", "medium", "low"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]

DISCLAIMER = (
    "SignalRoom is an educational financial research prototype. Its analysis is generated from "
    "available data and AI models and may contain errors. It does not provide personalized investment "
    "advice, execute trades, or guarantee the accuracy or completeness of market information."
)


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Source(Model):
    """A piece of evidence. URLs and publishers always come from providers, never from an LLM."""

    id: str
    title: str
    publisher: str | None = None
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str
    source_type: SourceType
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    provider: str | None = None
    tags: list[str] = Field(default_factory=list)


class ModelUsage(Model):
    provider: str
    model: str
    purpose: str
    agent: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int
    cost_usd: float | None = None
    ok: bool = True


class ErrorResponse(Model):
    error: str
    message: str
    request_id: str | None = None
