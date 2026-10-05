"""Deterministic fakes for providers and the AI gateway. Tests never call paid APIs."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from app.integrations.ai.audio_utils import pcm16_to_wav
from app.integrations.ai.base import AIUnavailableError, ModelRole, UsageTracker
from app.integrations.ai.gateway import AIGateway, SpeechOutput
from app.integrations.financial.base import FinancialDataError
from app.integrations.market.base import MarketDataError, Quote
from app.integrations.news.base import NewsProviderError, NewsQuery, NewsTimelines
from app.schemas.agents import Filing, FinancialSnapshot, NewsArticle, PricePoint, SeriesPoint
from app.schemas.assets import AssetMatch
from app.schemas.common import ModelUsage
from app.utils.ids import stable_id

NOW = datetime.now(UTC).replace(microsecond=0)


# --------------------------------------------------------------------------- market
def make_history(
    days: int = 130, last_move: float = -0.062, last_volume_mult: float = 2.8, start: float = 100.0
) -> list[PricePoint]:
    points: list[PricePoint] = []
    price = start
    base_day = (NOW - timedelta(days=days)).date()
    for i in range(days):
        drift = 0.004 * math.sin(i / 5.0) + 0.001
        if i == days - 1:
            drift = last_move
        open_ = price
        price = round(price * (1 + drift), 4)
        volume = 1_000_000 * (last_volume_mult if i == days - 1 else 1 + 0.1 * math.cos(i))
        points.append(
            PricePoint(
                time=(base_day + timedelta(days=i)).isoformat(),
                open=open_,
                high=max(open_, price) * 1.01,
                low=min(open_, price) * 0.99,
                close=price,
                volume=volume,
            )
        )
    return points


def make_intraday() -> list[PricePoint]:
    start = NOW.replace(hour=13, minute=30, second=0)
    out = []
    for i in range(78):
        p = 100 - i * 0.05
        out.append(
            PricePoint(
                time=(start + timedelta(minutes=5 * i)).isoformat(),
                open=p,
                high=p + 0.1,
                low=p - 0.1,
                close=p - 0.03,
                volume=10_000,
            )
        )
    return out


class FakeMarket:
    name = "fake_market"

    def __init__(self, fail: set[str] | None = None) -> None:
        self.fail = fail or set()
        self.calls: list[tuple[str, str]] = []

    async def get_history(self, symbol: str, range_: str = "6mo") -> list[PricePoint]:
        self.calls.append((symbol, range_))
        if symbol in self.fail or "*" in self.fail:
            raise MarketDataError(f"no data for {symbol}")
        if range_ == "1d":
            return make_intraday()
        if symbol == "^GSPC":
            return make_history(last_move=-0.012, last_volume_mult=1.0, start=5000)
        return make_history()

    async def get_quote(self, symbol: str) -> Quote:
        if symbol in self.fail or "*" in self.fail:
            raise MarketDataError("no quote")
        hist = make_history()
        return Quote(
            symbol=symbol,
            name={"NVDA": "NVIDIA Corporation"}.get(symbol, symbol),
            asset_type="equity",
            currency="USD",
            last_price=hist[-1].close,
            previous_close=hist[-2].close,
            retrieved_at=NOW.isoformat(),
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]:
        if query.upper().startswith("ZZZZ"):
            return []
        return [
            AssetMatch(
                symbol=query.upper(), name=f"{query.upper()} Inc.", asset_type="equity", source="provider"
            )
        ]


# --------------------------------------------------------------------------- news
THEMES = [
    (
        "export",
        [
            "U.S. tightens export rules on NVIDIA AI chips",
            "NVIDIA slides as Washington widens chip export curbs",
            "New export rules hit NVIDIA China chip sales",
            "Analysts weigh impact of chip export restrictions on NVIDIA",
            "NVIDIA warns export curbs could weigh on data center revenue",
        ],
        ["reuters.com", "bloomberg.com", "ft.com", "cnbc.com", "wsj.com"],
    ),
    (
        "valuation",
        [
            "NVIDIA valuation concerns grow after record rally",
            "Investors question NVIDIA valuation after record rally",
        ],
        ["barrons.com", "marketwatch.com"],
    ),
    ("partner", ["NVIDIA partner reports strong AI server demand"], ["nikkei.com"]),
]


def make_articles() -> list[NewsArticle]:
    arts: list[NewsArticle] = []
    for t_idx, (key, titles, pubs) in enumerate(THEMES):
        for p_idx, (title, pub) in enumerate(zip(titles, pubs, strict=True)):
            url = f"https://{pub}/news/{key}-{p_idx}"
            arts.append(
                NewsArticle(
                    id=stable_id("fk", url),
                    title=title,
                    url=url,
                    publisher=pub,
                    published_at=(NOW - timedelta(hours=6 + t_idx * 10 + p_idx)).isoformat(),
                    retrieved_at=NOW.isoformat(),
                    provider="fake_news",
                )
            )
    # an exact duplicate (syndication) that must be deduplicated
    arts.append(arts[0].model_copy(update={"id": "fk_dup"}))
    return arts


class FakeNewsProvider:
    name = "fake_news"

    def __init__(self, fail: bool = False, articles: list[NewsArticle] | None = None) -> None:
        self.fail = fail
        self.articles = articles if articles is not None else make_articles()

    async def search(self, query: NewsQuery) -> list[NewsArticle]:
        if self.fail:
            raise NewsProviderError("down")
        return list(self.articles)

    async def timelines(self, query: NewsQuery) -> NewsTimelines:
        tone = [
            SeriesPoint(date=(NOW - timedelta(days=d)).isoformat(), value=1.0 - d * 0.0 if d > 2 else -2.5)
            for d in range(7, -1, -1)
        ]
        return NewsTimelines(
            tone=tone, volume=[SeriesPoint(date=p.date, value=10 + i) for i, p in enumerate(tone)]
        )


# --------------------------------------------------------------------------- financial
class FakeFinancial:
    name = "fake_sec"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def snapshot(self, symbol: str) -> FinancialSnapshot:
        if self.fail:
            raise FinancialDataError("down")
        if symbol.startswith("^") or symbol.endswith("-USD"):
            return FinancialSnapshot(applicable=False, note="not applicable")
        return FinancialSnapshot(
            entity_name="NVIDIA CORP",
            cik="0001045810",
            fiscal_period="quarter",
            period_end=(NOW - timedelta(days=60)).date().isoformat(),
            revenue=46.7e9,
            revenue_growth_yoy=0.56,
            revenue_growth_qoq=0.06,
            operating_income=28.4e9,
            operating_margin=0.61,
            net_income=26.4e9,
            net_margin=0.56,
            cash=11.6e9,
            debt=8.5e9,
            recent_filings=[
                Filing(
                    form="10-Q",
                    filed=(NOW - timedelta(days=30)).date().isoformat(),
                    description="Quarterly report",
                    url="https://www.sec.gov/Archives/edgar/data/1045810/x/q.htm",
                ),
                Filing(
                    form="8-K",
                    filed=(NOW - timedelta(days=3)).date().isoformat(),
                    description="Current report",
                    url="https://www.sec.gov/Archives/edgar/data/1045810/y/k.htm",
                ),
            ],
        )


# --------------------------------------------------------------------------- AI gateway
Handler = Callable[[dict[str, Any]], Any]


def _payload(user: str) -> dict[str, Any]:
    try:
        data = json.loads(user)
        return data if isinstance(data, dict) else {"raw": user}
    except json.JSONDecodeError:
        return {"raw": user}


def default_handlers() -> dict[str, Handler]:
    def plan(p: dict[str, Any]) -> dict[str, Any]:
        # Deliberately minimal: enforce_constraints must add the intent's minimum team.
        return {
            "intent": "why_move",
            "agents": ["market", "news"],
            "rationale": "Price move question.",
            "time_window_days": 7,
        }

    def labels(p: dict[str, Any]) -> dict[str, Any]:
        out = []
        for i, c in enumerate(p["clusters"]):
            title = c["headlines"][0]["title"].lower()
            relevance = 0.1 if "partner" in title else 0.9  # partner story judged off-topic → filtered
            out.append(
                {
                    "cluster_id": c["cluster_id"],
                    "theme": "Export restrictions" if "export" in title else f"Theme {i}",
                    "summary": "Headlines report the topic.",
                    "event_type": "regulation" if "export" in title else "other",
                    "tone": -0.7 if "export" in title else -0.2,
                    "relevance": relevance,
                }
            )
        return {"clusters": out}

    def risk(p: dict[str, Any]) -> dict[str, Any]:
        cluster = next((e["id"] for e in p["evidence"] if e["type"] == "news_cluster"), "unknown")
        return {
            "items": [
                {
                    "risk": "regulatory",
                    "level": "HIGH",
                    "reason": "Export rules reported by several publishers.",
                    "evidence_ids": [cluster, "made_up_id"],
                },
                {
                    "risk": "valuation",
                    "level": "MEDIUM",
                    "reason": "Unsupported risk.",
                    "evidence_ids": ["made_up_id"],
                },
            ]
        }

    def synthesis(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "executive_summary": "NVIDIA fell sharply. Export news caused the stock to fall. You should buy the dip.",
            "what_happened": "The stock declined in the latest session on heavy volume.",
            "drivers": [
                {"driver_id": d["driver_id"], "explanation": f"Explanation for {d['name']}."}
                for d in p["drivers"]
            ],
            "market_context": "Benchmark also declined.",
            "financial_context": "Fundamentals remain strong.",
            "sentiment_summary": "Tone turned negative.",
            "risk_summary": "Regulatory risk is elevated.",
            "what_to_watch": ["Further export guidance", "Next earnings date"],
            "uncertainties": ["Timing of headlines vs the move"],
            "claims": [
                {
                    "claim": "Fabricated fact with no evidence.",
                    "claim_type": "observed_fact",
                    "evidence_ids": ["nope"],
                },
                {
                    "claim": "Interpretation without evidence.",
                    "claim_type": "interpretation",
                    "evidence_ids": [],
                },
                {
                    "claim": "Export news is the main reported concern.",
                    "claim_type": "interpretation",
                    "evidence_ids": [d["evidence_ids"][0] for d in p["drivers"] if d["evidence_ids"]][:1],
                },
            ],
        }

    def transcription(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "language": "en",
            "speakers": ["Operator", "CEO"],
            "segments": [
                {"speaker": "Operator", "start": "00:00", "text": "Welcome to the call."},
                {
                    "speaker": "CEO",
                    "start": "00:10",
                    "text": "Revenue grew 31 percent and we expect export headwinds next quarter.",
                },
            ],
        }

    def earnings(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "Strong quarter, cautious outlook.",
            "key_points": ["Revenue grew 31 percent"],
            "guidance": ["Export headwinds next quarter"],
            "management_tone": "cautious",
            "risks": ["Export restrictions"],
            "notable_quotes": ["Revenue grew 31 percent", "We will triple revenue next year"],
        }

    return {
        "plan": plan,
        "label_clusters": labels,
        "risk_assessment": risk,
        "synthesis": synthesis,
        "transcription": transcription,
        "voice_command": lambda p: {
            "language": "en",
            "speakers": ["User"],
            "segments": [{"speaker": "User", "text": "Why did Nvidia fall today?"}],
        },
        "earnings_analysis": earnings,
        "video_analysis": lambda p: {
            "summary": "Northwind CEO presents Q3 results: revenue up 18 percent, margin pressure from logistics.",
            "language": "en",
            "speakers": ["CEO", "CFO"],
            "segments": [
                {
                    "speaker": "CEO",
                    "start": "00:05",
                    "text": "Revenue grew 18 percent to 4.2 billion dollars this quarter.",
                },
                {
                    "speaker": "CFO",
                    "start": "00:40",
                    "text": "Logistics costs compressed gross margin by 120 basis points.",
                },
            ],
            "slides": [
                {
                    "timestamp": "00:20",
                    "title": "Q3 FY2026 highlights",
                    "description": "Revenue and margin bar chart",
                    "figures": [
                        {"fact": "Revenue", "value": "$4.2B"},
                        {"fact": "Gross margin", "value": "41.3%"},
                    ],
                }
            ],
            "key_points": ["Revenue grew 18 percent"],
            "guidance": ["FY revenue growth of 15-17 percent"],
            "management_tone": "confident",
            "risks": ["Logistics costs"],
            "notable_quotes": [
                "Revenue grew 18 percent to 4.2 billion dollars this quarter.",
                "We will double margins",
            ],
        },
        "document_text": lambda p: {
            "summary": "Revenue rose to $4.2 billion.",
            "key_facts": [{"fact": "Revenue", "value": "$4.2 billion", "page": 1}],
            "risks": ["Export licences"],
            "guidance": ["Q4 revenue $4.0-4.2B"],
        },
        "document_vision": lambda p: {
            "pages": [
                {
                    "page": 2,
                    "content_type": "financial_table",
                    "description": "Income statement table",
                    "extracted_figures": [{"fact": "Net income", "value": "1,071", "page": 2}],
                }
            ]
        },
        "image_analysis": lambda p: {
            "image_type": "price_chart",
            "observations": ["Uptrend"],
            "uncertainties": ["No volume"],
            "relevant_levels": ["238"],
            "detected_symbol": "NVDA",
            "interpretation": "The chart appears to show an uptrend.",
        },
        "followup_answer": lambda p: {
            "answer": "A reversal of the export rules would invalidate it.",
            "evidence_ids": [
                p["drivers"][0]["evidence_ids"][0]
                if p.get("drivers") and p["drivers"][0]["evidence_ids"]
                else "x",
                "invented",
            ],
            "needs_new_data": False,
        },
        "daily_briefing": lambda p: {
            "headline": "NVIDIA leads the watchlist lower",
            "greeting": "Good morning.",
            "summary": "Three things matter today.",
            "sections": [
                {
                    "title": "NVIDIA",
                    "symbol": "NVDA",
                    "body": "Shares fell.",
                    "why_it_matters": "Largest mover.",
                    "source_ids": ["src_mkt_nvda", "fake_source"],
                }
            ],
            "risk_flags": ["Export rules"],
            "macro_events": ["Yields rose"],
        },
    }


def _bow_vector(text: str, dim: int = 256) -> list[float]:
    """Deterministic hashed bag-of-words: texts sharing words get a high cosine (stands in for embeddings)."""
    vec = [0.0] * dim
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) > 2:
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % dim] += 1.0
    vec[0] += 0.1
    return vec


class FakeGateway(AIGateway):
    def __init__(
        self,
        handlers: dict[str, Handler] | None = None,
        roles: set[str] | None = None,
        tracker: UsageTracker | None = None,
        fail_purposes: set[str] | None = None,
    ) -> None:
        super().__init__({}, tracker=tracker)
        self.handlers = handlers if handlers is not None else default_handlers()
        self.roles = (
            roles
            if roles is not None
            else {"reasoning", "vision", "transcription", "tts", "image", "embedding"}
        )
        self.fail_purposes = fail_purposes or set()
        self.calls: list[str] = []

    def with_tracker(self, tracker: UsageTracker) -> FakeGateway:
        clone = FakeGateway(self.handlers, self.roles, tracker, self.fail_purposes)
        clone.calls = self.calls
        return clone

    def available(self, role: ModelRole) -> bool:
        return role in self.roles

    def model_for(self, role: ModelRole) -> str | None:
        return f"fake-{role}" if role in self.roles else None

    async def embed_texts(
        self, texts: list[str], *, agent: str = "search", batch_size: int = 64
    ) -> list[list[float]]:
        self.calls.append("embedding_text")
        if "embedding" not in self.roles:
            raise AIUnavailableError("embedding")
        self.tracker.add(
            ModelUsage(
                provider="fake",
                model="fake-embedding",
                purpose="embedding_text",
                agent=agent,
                latency_ms=1,
                cost_usd=0.00001,
            )
        )
        return [_bow_vector(t) for t in texts]

    async def embed_image(self, data: bytes, mime_type: str, *, agent: str = "search") -> list[float]:
        self.calls.append("embedding_image")
        if "embedding" not in self.roles:
            raise AIUnavailableError("embedding")
        self.tracker.add(
            ModelUsage(
                provider="fake",
                model="fake-embedding",
                purpose="embedding_image",
                agent=agent,
                latency_ms=1,
                cost_usd=0.00001,
            )
        )
        return _bow_vector(f"image {hashlib.sha256(data).hexdigest()}")

    def describe(self) -> dict[str, dict[str, str]]:
        return {r: {"provider": "fake", "model": f"fake-{r}"} for r in self.roles}

    async def structured(
        self,
        schema: type[BaseModel],
        *,
        system: str,
        user: str,
        agent: str,
        purpose: str,
        role: ModelRole = "reasoning",
        **_: Any,
    ) -> Any:  # type: ignore[override]
        self.calls.append(purpose)
        if role not in self.roles:
            raise AIUnavailableError(role)
        if purpose in self.fail_purposes or purpose not in self.handlers:
            from app.integrations.ai.base import AIResponseError

            raise AIResponseError(f"fake failure for {purpose}")
        self.tracker.add(
            ModelUsage(
                provider="fake",
                model=f"fake-{role}",
                purpose=purpose,
                agent=agent,
                latency_ms=1,
                cost_usd=0.0001,
                input_tokens=10,
                output_tokens=5,
            )
        )
        return schema.model_validate(self.handlers[purpose](_payload(user)))

    async def speech(self, text: str, *, agent: str = "voice", style: str = "") -> SpeechOutput:
        self.calls.append("tts")
        if "tts" not in self.roles:
            raise AIUnavailableError("tts")
        self.tracker.add(
            ModelUsage(provider="fake", model="fake-tts", purpose="tts", agent=agent, latency_ms=1)
        )
        return SpeechOutput(wav=pcm16_to_wav(b"\x00\x00" * 2400), duration_seconds=0.1)

    async def image(self, prompt: str, *, agent: str = "infographic") -> tuple[bytes, str]:
        self.calls.append("image")
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (16, 9), (8, 9, 13)).save(buf, format="PNG")
        return buf.getvalue(), "image/png"
