"""LangGraph state for an investigation. Reducers make parallel agent branches safe."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.agents import AgentRun
from app.schemas.common import Source


def merge_sources(left: list[Source] | None, right: list[Source] | None) -> list[Source]:
    """Union of sources by id (first occurrence wins, order preserved)."""
    out: dict[str, Source] = {}
    for src in (left or []) + (right or []):
        out.setdefault(src.id, src)
    return list(out.values())


def last_value(left: Any, right: Any) -> Any:
    return right if right is not None else left


class InvestigationState(TypedDict, total=False):
    # inputs
    investigation_id: str
    user_id: str
    symbol: str | None
    asset_name: Annotated[str | None, last_value]
    asset_type: str | None
    question: str
    attachments: list[Any]
    generate_audio: bool
    # orchestrator
    plan: Any
    # collectors
    market: Any
    news: Any
    financial: Any
    macro: Any
    documents: list[Any]
    images: list[Any]
    audio: list[Any]
    videos: list[Any]
    # analysis
    sentiment: Any
    events: Any
    risks: Any
    evidence: Any
    synthesis: Any
    ai_narrative_available: bool
    # outputs
    audio_key: str | None
    audio_duration: float | None
    # accumulated across branches
    sources: Annotated[list[Source], merge_sources]
    agent_runs: Annotated[list[AgentRun], operator.add]
    warnings: Annotated[list[str], operator.add]
