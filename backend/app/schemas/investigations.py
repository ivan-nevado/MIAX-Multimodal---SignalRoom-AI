from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.agents import (
    AgentPlan,
    AgentRun,
    AudioFindings,
    Claim,
    DocumentFindings,
    Driver,
    EventFindings,
    FinancialSnapshot,
    ImageFindings,
    MacroFindings,
    MarketFindings,
    NewsFindings,
    RiskFindings,
    SentimentFindings,
    VideoFindings,
)
from app.schemas.common import DISCLAIMER, Model, ModelUsage, Source

MediaStatus = Literal["none", "pending", "ready", "failed"]


class AttachmentRef(Model):
    upload_id: str
    kind: Literal["document", "image", "audio", "video"]
    filename: str
    content_type: str
    storage_key: str
    size_bytes: int = 0


class FollowUp(Model):
    followup_id: str
    question: str
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    agents_run: list[str] = Field(default_factory=list)
    upload_ids: list[str] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None


class InvestigationResult(Model):
    symbol: str | None
    asset_name: str | None
    question: str
    intent: str
    executive_summary: str
    what_happened: str
    drivers: list[Driver] = Field(default_factory=list)
    market_context: str = ""
    financial_context: str = ""
    sentiment_summary: str = ""
    risk_summary: str = ""
    what_to_watch: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    market: MarketFindings | None = None
    news: NewsFindings | None = None
    sentiment: SentimentFindings | None = None
    events: EventFindings | None = None
    financial: FinancialSnapshot | None = None
    macro: MacroFindings | None = None
    risks: RiskFindings | None = None
    documents: list[DocumentFindings] = Field(default_factory=list)
    images: list[ImageFindings] = Field(default_factory=list)
    audio: list[AudioFindings] = Field(default_factory=list)
    videos: list[VideoFindings] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    agent_runs: list[AgentRun] = Field(default_factory=list)
    model_usage: list[ModelUsage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ai_narrative_available: bool = True
    generated_at: str
    disclaimer: str = DISCLAIMER


class InvestigationRecord(Model):
    investigation_id: str
    user_id: str
    symbol: str | None = None
    asset_name: str | None = None
    asset_type: str | None = None
    question: str
    status: str = "queued"
    progress: int = 0
    current_agent: str | None = None
    status_message: str = "Queued"
    plan: AgentPlan | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)
    generate_audio: bool = False
    result: InvestigationResult | None = None
    summary: str | None = None
    error: str | None = None
    audio_key: str | None = None
    audio_status: MediaStatus = "none"
    infographic_key: str | None = None
    infographic_status: MediaStatus = "none"
    followups: list[FollowUp] = Field(default_factory=list)
    attempts: int = 0
    created_at: str
    updated_at: str
    completed_at: str | None = None


class InvestigationEvent(Model):
    investigation_id: str
    seq: int
    timestamp: str
    event_type: str
    message: str
    agent: str | None = None
    progress: int | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- API contracts
class CreateInvestigationRequest(Model):
    asset: str | None = Field(default=None, max_length=64)
    question: str = Field(default="Why did this asset move today?", min_length=3, max_length=600)
    upload_ids: list[str] = Field(default_factory=list, max_length=6)
    generate_audio: bool = False

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class CreateInvestigationResponse(Model):
    investigation_id: str
    status: str


class InvestigationSummary(Model):
    investigation_id: str
    symbol: str | None
    asset_name: str | None
    question: str
    status: str
    progress: int
    summary: str | None
    move_pct: float | None = None
    created_at: str
    completed_at: str | None


class InvestigationView(Model):
    """Investigation as returned to the browser (signed media URLs, no storage keys)."""

    investigation_id: str
    symbol: str | None
    asset_name: str | None
    asset_type: str | None
    question: str
    status: str
    progress: int
    current_agent: str | None
    status_message: str
    plan: AgentPlan | None
    attachments: list[dict[str, Any]]
    result: InvestigationResult | None
    error: str | None
    audio_status: MediaStatus
    audio_url: str | None
    infographic_status: MediaStatus
    infographic_url: str | None
    followups: list[FollowUp]
    created_at: str
    updated_at: str
    completed_at: str | None


class FollowUpRequest(Model):
    question: str = Field(min_length=3, max_length=600)
    upload_ids: list[str] = Field(default_factory=list, max_length=4)


class FollowUpResponse(Model):
    followup_id: str
    status: str


class MediaJobResponse(Model):
    status: MediaStatus
