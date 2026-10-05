from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import DISCLAIMER, Model, ModelUsage, Source

BriefingStatus = Literal["queued", "running", "completed", "failed"]


class WatchlistMove(Model):
    symbol: str
    name: str | None = None
    last_price: float | None = None
    move_pct: float | None = None
    return_5d_pct: float | None = None
    volume_change_pct: float | None = None
    unusual_move: bool = False
    currency: str | None = None


class BriefingSection(Model):
    title: str = Field(max_length=120)
    symbol: str | None = None
    body: str = Field(max_length=900)
    why_it_matters: str = Field(default="", max_length=500)
    source_ids: list[str] = Field(default_factory=list)


class BriefingLLMOutput(Model):
    headline: str = Field(max_length=160)
    greeting: str = Field(default="Good morning.", max_length=120)
    summary: str = Field(max_length=900)
    sections: list[BriefingSection] = Field(default_factory=list, max_length=5)
    risk_flags: list[str] = Field(default_factory=list, max_length=6)
    macro_events: list[str] = Field(default_factory=list, max_length=6)


class Briefing(Model):
    briefing_id: str
    user_id: str
    date: str
    briefing_type: Literal["daily", "on_demand"] = "daily"
    status: BriefingStatus = "queued"
    headline: str | None = None
    greeting: str | None = None
    summary: str | None = None
    sections: list[BriefingSection] = Field(default_factory=list)
    top_events: list[str] = Field(default_factory=list)
    watchlist_moves: list[WatchlistMove] = Field(default_factory=list)
    macro_events: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    audio_key: str | None = None
    audio_status: Literal["none", "pending", "ready", "failed"] = "none"
    audio_duration_seconds: float | None = None
    email_status: Literal["not_requested", "pending", "sent", "failed", "skipped"] = "not_requested"
    model_usage: list[ModelUsage] = Field(default_factory=list)
    error: str | None = None
    ai_narrative_available: bool = True
    created_at: str
    completed_at: str | None = None
    disclaimer: str = DISCLAIMER


class BriefingView(Briefing):
    audio_url: str | None = None


class BriefingSummary(Model):
    briefing_id: str
    date: str
    briefing_type: str
    status: str
    headline: str | None
    audio_status: str
    created_at: str


class GenerateBriefingRequest(Model):
    with_audio: bool = True
    send_email: bool = False


class GenerateBriefingResponse(Model):
    briefing_id: str
    status: str
