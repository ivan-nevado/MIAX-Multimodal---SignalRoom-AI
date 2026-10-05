"""Agent infrastructure: dependency-injected context and a common output contract.

Agents depend only on interfaces (AIGateway, MarketDataProvider, ...). They never
import yfinance, httpx, boto3, openai or google SDKs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.config.settings import Settings
from app.integrations.ai.gateway import AIGateway
from app.integrations.financial.base import FinancialDataProvider
from app.integrations.macro.base import MacroDataProvider
from app.integrations.market.base import MarketDataProvider
from app.integrations.news.composite import CompositeNewsProvider
from app.integrations.storage.base import StorageBackend


class AgentSkipped(Exception):
    """Raised when an agent has nothing to do (e.g. no attachment of its type)."""


@dataclass
class AgentContext:
    ai: AIGateway
    market: MarketDataProvider
    news: CompositeNewsProvider
    financial: FinancialDataProvider | None
    macro_providers: list[MacroDataProvider]
    storage: StorageBackend
    settings: Settings


@dataclass
class AgentOutput:
    update: dict[str, Any]
    summary: str
    warnings: list[str] = field(default_factory=list)


class Agent(Protocol):
    name: str
    label: str

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput: ...


AGENT_LABELS: dict[str, str] = {
    "orchestrator": "Orchestrator",
    "market": "Market Agent",
    "news": "News Agent",
    "financial": "Financial Agent",
    "macro": "Macro Agent",
    "document": "Document Agent",
    "vision": "Vision Agent",
    "audio": "Audio Agent",
    "video": "Video Agent",
    "sentiment": "Sentiment Agent",
    "event_detection": "Event Detection Agent",
    "risk": "Risk Agent",
    "evidence": "Evidence Agent",
    "synthesis": "Synthesis Agent",
    "voice": "Voice Agent",
    "briefing": "Briefing Agent",
    "followup": "Research Analyst",
    "infographic": "Visual Brief Agent",
}

# Progress event type per agent (what the frontend timeline shows).
AGENT_EVENT_TYPES: dict[str, str] = {
    "orchestrator": "planning",
    "market": "market_data",
    "news": "news",
    "financial": "financial",
    "macro": "macro",
    "document": "document",
    "vision": "image",
    "audio": "audio_transcript",
    "video": "video",
    "sentiment": "sentiment",
    "event_detection": "events",
    "risk": "risk",
    "evidence": "evidence",
    "synthesis": "synthesis",
    "voice": "audio",
}
