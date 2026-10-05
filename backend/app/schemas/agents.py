"""Structured outputs of every agent. Every LLM response is validated against these models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import EvidenceConfidence, Model, RiskLevel

AgentName = Literal[
    "orchestrator",
    "market",
    "news",
    "financial",
    "macro",
    "document",
    "vision",
    "audio",
    "video",
    "sentiment",
    "event_detection",
    "risk",
    "evidence",
    "synthesis",
    "voice",
    "briefing",
    "followup",
    "infographic",
]

COLLECTION_AGENTS: tuple[str, ...] = (
    "market",
    "news",
    "financial",
    "macro",
    "document",
    "vision",
    "audio",
    "video",
)
ANALYSIS_AGENTS: tuple[str, ...] = ("sentiment", "event_detection")

EventType = Literal[
    "earnings",
    "guidance_change",
    "regulation",
    "lawsuit",
    "management_change",
    "m_and_a",
    "product",
    "analyst_action",
    "macro",
    "sector_move",
    "market_move",
    "filing",
    "other",
]


# --------------------------------------------------------------------------- orchestrator
class AgentPlan(Model):
    intent: Literal["why_move", "earnings_review", "document_review", "chart_review", "general_research"]
    agents: list[str]
    rationale: str
    time_window_days: int = Field(default=7, ge=1, le=90)


# --------------------------------------------------------------------------- market
class PricePoint(Model):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class MarketMetrics(Model):
    symbol: str
    currency: str | None = None
    as_of: str | None = None
    last_price: float | None = None
    previous_close: float | None = None
    move_pct: float | None = None
    return_5d_pct: float | None = None
    return_1m_pct: float | None = None
    volume: float | None = None
    avg_volume_20d: float | None = None
    volume_change_pct: float | None = None
    volatility_20d: float | None = None
    drawdown_30d: float | None = None
    zscore_move: float | None = None
    anomaly_score: float | None = None
    ma_20: float | None = None
    ma_50: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    benchmark_symbol: str | None = None
    benchmark_move_pct: float | None = None
    relative_performance_pct: float | None = None
    unusual_move: bool = False
    observations: list[str] = Field(default_factory=list)


class MarketFindings(Model):
    metrics: MarketMetrics
    history: list[PricePoint] = Field(default_factory=list)
    intraday: list[PricePoint] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- news
class NewsArticle(Model):
    id: str
    title: str
    url: str
    publisher: str
    published_at: str | None = None
    retrieved_at: str
    provider: str
    tone: float | None = None
    relevance: float = 0.5
    query: str | None = None


class NewsCluster(Model):
    cluster_id: str
    theme: str
    summary: str = ""
    event_type: EventType = "other"
    tone: float | None = Field(default=None, ge=-1.0, le=1.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    article_ids: list[str] = Field(default_factory=list)
    first_seen: str | None = None
    source_count: int = 0


class SeriesPoint(Model):
    date: str
    value: float


class NewsFindings(Model):
    query: str
    articles_reviewed: int = 0
    articles: list[NewsArticle] = Field(default_factory=list)
    clusters: list[NewsCluster] = Field(default_factory=list)
    tone_timeline: list[SeriesPoint] = Field(default_factory=list)
    volume_timeline: list[SeriesPoint] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)


class ClusterLabel(Model):
    """LLM output for one cluster (themes are summarised from headlines only)."""

    cluster_id: str
    theme: str = Field(max_length=80)
    summary: str = Field(max_length=400)
    event_type: EventType = "other"
    tone: float = Field(ge=-1.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)


class ClusterLabels(Model):
    clusters: list[ClusterLabel]


# --------------------------------------------------------------------------- sentiment
class SentimentFindings(Model):
    overall_tone: float | None = None
    recent_tone: float | None = None
    prior_tone: float | None = None
    sentiment_change: float | None = None
    label: Literal["positive", "neutral", "negative", "unknown"] = "unknown"
    agreement: Literal["aligned", "mixed", "divergent", "unknown"] = "unknown"
    evidence_confidence: EvidenceConfidence = "low"
    confidence_reason: str = ""
    timeline: list[SeriesPoint] = Field(default_factory=list)
    cluster_sentiment: list[dict[str, object]] = Field(default_factory=list)


# --------------------------------------------------------------------------- events
class TimelineEvent(Model):
    id: str
    timestamp: str
    event_type: EventType
    title: str
    description: str = ""
    origin: Literal["news", "market", "filing", "document", "audio", "image", "video"]
    source_ids: list[str] = Field(default_factory=list)


class EventFindings(Model):
    events: list[TimelineEvent] = Field(default_factory=list)


# --------------------------------------------------------------------------- financial
class Filing(Model):
    form: str
    filed: str
    description: str | None = None
    url: str | None = None


class FinancialSnapshot(Model):
    applicable: bool = True
    note: str | None = None
    entity_name: str | None = None
    cik: str | None = None
    fiscal_period: str | None = None
    period_end: str | None = None
    revenue: float | None = None
    revenue_growth_yoy: float | None = None
    revenue_growth_qoq: float | None = None
    operating_income: float | None = None
    operating_margin: float | None = None
    net_income: float | None = None
    net_margin: float | None = None
    assets: float | None = None
    liabilities: float | None = None
    cash: float | None = None
    debt: float | None = None
    shares_outstanding: float | None = None
    recent_filings: list[Filing] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- macro
class MacroIndicator(Model):
    id: str
    name: str
    value: float | None = None
    change: float | None = None
    unit: str = ""
    as_of: str | None = None
    provider: str
    series: list[SeriesPoint] = Field(default_factory=list)
    source_id: str | None = None


class MacroFindings(Model):
    indicators: list[MacroIndicator] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- uploads
class DocumentFact(Model):
    fact: str
    value: str | None = None
    page: int | None = None


class DocumentLLMOutput(Model):
    summary: str
    key_facts: list[DocumentFact] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)


class PageVisualAnalysis(Model):
    page: int
    content_type: Literal["financial_table", "chart", "text", "mixed", "other"] = "other"
    description: str
    extracted_figures: list[DocumentFact] = Field(default_factory=list)


class DocumentFindings(Model):
    upload_id: str
    filename: str
    page_count: int
    pages_analyzed: list[int] = Field(default_factory=list)
    text_chars: int = 0
    summary: str = ""
    key_facts: list[DocumentFact] = Field(default_factory=list)
    visual_pages: list[PageVisualAnalysis] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    source_id: str | None = None


class ImageAnalysis(Model):
    image_type: Literal[
        "price_chart", "financial_table", "presentation_slide", "document", "dashboard", "other"
    ] = "other"
    observations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    relevant_levels: list[str] = Field(default_factory=list)
    detected_symbol: str | None = None
    interpretation: str = ""


class ImageFindings(ImageAnalysis):
    upload_id: str
    filename: str
    source_id: str | None = None


class TranscriptSegment(Model):
    speaker: str = "Speaker"
    start: str | None = None
    text: str


class Transcript(Model):
    language: str = "unknown"
    speakers: list[str] = Field(default_factory=list)
    segments: list[TranscriptSegment] = Field(default_factory=list)


class EarningsCallAnalysis(Model):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    management_tone: Literal["confident", "cautious", "defensive", "mixed", "neutral"] = "neutral"
    risks: list[str] = Field(default_factory=list)
    notable_quotes: list[str] = Field(default_factory=list)


class AudioFindings(Model):
    upload_id: str
    filename: str
    language: str = "unknown"
    speakers: list[str] = Field(default_factory=list)
    segment_count: int = 0
    transcript_key: str | None = None
    transcript_preview: list[TranscriptSegment] = Field(default_factory=list)
    analysis: EarningsCallAnalysis | None = None
    source_id: str | None = None


class VideoSlide(Model):
    timestamp: str | None = None
    title: str = ""
    description: str = ""
    figures: list[DocumentFact] = Field(default_factory=list)


class VideoAnalysis(Model):
    """One Gemini call reads the speech AND what is shown on screen (slides, charts, tables)."""

    summary: str
    language: str = "unknown"
    speakers: list[str] = Field(default_factory=list)
    segments: list[TranscriptSegment] = Field(default_factory=list)
    slides: list[VideoSlide] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    management_tone: Literal["confident", "cautious", "defensive", "mixed", "neutral"] = "neutral"
    risks: list[str] = Field(default_factory=list)
    notable_quotes: list[str] = Field(default_factory=list)


class VideoFindings(Model):
    upload_id: str
    filename: str
    summary: str = ""
    language: str = "unknown"
    speakers: list[str] = Field(default_factory=list)
    segment_count: int = 0
    transcript_key: str | None = None
    transcript_preview: list[TranscriptSegment] = Field(default_factory=list)
    slides: list[VideoSlide] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    management_tone: str = "neutral"
    risks: list[str] = Field(default_factory=list)
    notable_quotes: list[str] = Field(default_factory=list)
    source_id: str | None = None


# --------------------------------------------------------------------------- risk
class RiskItem(Model):
    risk: Literal[
        "regulatory",
        "valuation",
        "operational",
        "competition",
        "macro",
        "liquidity",
        "concentration",
        "governance",
        "market",
    ]
    level: RiskLevel
    reason: str = Field(max_length=500)
    evidence_ids: list[str] = Field(default_factory=list)


class RiskFindings(Model):
    items: list[RiskItem] = Field(default_factory=list)


# --------------------------------------------------------------------------- evidence / synthesis
class DriverComponents(Model):
    relevance: float
    source_support: float
    temporal_alignment: float
    sentiment_shift: float


class Driver(Model):
    driver_id: str
    name: str
    category: str
    explanation: str = ""
    contribution_score: float = Field(ge=0.0, le=100.0)
    raw_score: float = 0.0
    components: DriverComponents | None = None
    evidence_ids: list[str] = Field(default_factory=list)


ClaimType = Literal["observed_fact", "derived_metric", "interpretation", "hypothesis"]


class Claim(Model):
    claim_id: str
    claim: str
    claim_type: ClaimType
    evidence_ids: list[str] = Field(default_factory=list)
    source_count: int = 0
    evidence_confidence: EvidenceConfidence = "low"


class EvidenceFindings(Model):
    drivers: list[Driver] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    independent_sources: int = 0


class SynthesisDriver(Model):
    driver_id: str
    explanation: str = Field(max_length=700)


class SynthesisClaim(Model):
    claim: str = Field(max_length=400)
    claim_type: ClaimType
    evidence_ids: list[str] = Field(default_factory=list)


class SynthesisOutput(Model):
    """What the synthesis LLM may write. Numbers and sources are NOT part of this contract."""

    executive_summary: str = Field(max_length=1200)
    what_happened: str = Field(max_length=1500)
    drivers: list[SynthesisDriver] = Field(default_factory=list)
    market_context: str = Field(default="", max_length=1200)
    financial_context: str = Field(default="", max_length=1200)
    sentiment_summary: str = Field(default="", max_length=800)
    risk_summary: str = Field(default="", max_length=1000)
    what_to_watch: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    claims: list[SynthesisClaim] = Field(default_factory=list)


class RiskLLMOutput(Model):
    items: list[RiskItem]


class FollowUpLLMOutput(Model):
    answer: str = Field(max_length=2500)
    evidence_ids: list[str] = Field(default_factory=list)
    needs_new_data: bool = False


class FollowUpRouting(Model):
    agents: list[str] = Field(default_factory=list)
    rationale: str = ""


class AgentRun(Model):
    agent: str
    status: Literal["completed", "failed", "skipped"]
    summary: str
    started_at: str
    finished_at: str
    duration_ms: int
