"""Event Detection Agent — turns news clusters, market sessions, filings and uploads into a timeline."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.analytics.metrics import daily_log_returns, z_score
from app.schemas.agents import EventFindings, FinancialSnapshot, MarketFindings, NewsFindings, TimelineEvent
from app.utils.ids import stable_id
from app.utils.time import parse_iso, utc_now

MAX_EVENTS = 16


def market_events(market: MarketFindings) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    hist = market.history
    m = market.metrics
    closes = [p.close for p in hist]
    rets = daily_log_returns(closes)
    vols = [p.volume or 0.0 for p in hist]
    # Unusual sessions in the last 10 sessions (|z| ≥ 2 or volume ≥ 2× its 20-session average).
    for i in range(max(len(hist) - 10, 21), len(hist)):
        z = z_score(float(rets[i - 1]), rets[max(0, i - 61) : i - 1]) if i - 1 < len(rets) else None
        base_vol = sum(vols[i - 20 : i]) / 20 if i >= 20 else 0
        vol_ratio = vols[i] / base_vol if base_vol else 0
        if (z is not None and abs(z) >= 2) or vol_ratio >= 2:
            change = (closes[i] / closes[i - 1] - 1) * 100
            parts = []
            if z is not None and abs(z) >= 2:
                parts.append(f"{change:+.2f}% ({abs(z):.1f}σ)")
            if vol_ratio >= 2:
                parts.append(f"volume {vol_ratio:.1f}× average")
            events.append(
                TimelineEvent(
                    id=stable_id("ev", m.symbol, hist[i].time, "mkt"),
                    timestamp=hist[i].time,
                    event_type="market_move",
                    title="Unusual session" if z is not None and abs(z) >= 2 else "Volume spike",
                    description=", ".join(parts),
                    origin="market",
                    source_ids=market.source_ids[:1],
                )
            )
    if market.intraday:
        low = min(market.intraday, key=lambda p: p.low)
        high = max(market.intraday, key=lambda p: p.high)
        for point, label, value in (
            (low, "Price reached session low", low.low),
            (high, "Price reached session high", high.high),
        ):
            events.append(
                TimelineEvent(
                    id=stable_id("ev", m.symbol, point.time, label),
                    timestamp=point.time,
                    event_type="market_move",
                    title=label,
                    description=f"{value:,.2f}",
                    origin="market",
                    source_ids=market.source_ids[:1],
                )
            )
    return events


def news_events(news: NewsFindings) -> list[TimelineEvent]:
    out = []
    for c in news.clusters:
        if not c.first_seen:
            continue
        out.append(
            TimelineEvent(
                id=stable_id("ev", c.cluster_id),
                timestamp=c.first_seen,
                event_type=c.event_type,
                title=c.theme,
                description=c.summary
                or f"{len(c.article_ids)} related articles from {c.source_count} publishers",
                origin="news",
                source_ids=c.article_ids[:3],
            )
        )
    return out


def filing_events(fin: FinancialSnapshot, window_days: int) -> list[TimelineEvent]:
    out = []
    now = utc_now()
    for f, sid in zip(fin.recent_filings, fin.source_ids[1:], strict=False):
        filed = parse_iso(f.filed)
        if filed is None or (now - filed).days > max(window_days, 45):
            continue
        out.append(
            TimelineEvent(
                id=stable_id("ev", f.form, f.filed),
                timestamp=f.filed,
                event_type="earnings" if f.form in ("10-Q", "10-K") else "filing",
                title=f"{f.form} filed with the SEC",
                description=f.description or "",
                origin="filing",
                source_ids=[sid],
            )
        )
    return out


class EventDetectionAgent:
    name = "event_detection"
    label = "Event Detection Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        events: list[TimelineEvent] = []
        plan = state.get("plan")
        window = plan.time_window_days if plan else 7
        if state.get("news"):
            events += news_events(state["news"])
        if state.get("market"):
            events += market_events(state["market"])
        fin = state.get("financial")
        if fin is not None and fin.applicable:
            events += filing_events(fin, window)
        for clip in state.get("audio") or []:
            if clip.analysis and clip.analysis.guidance:
                events.append(
                    TimelineEvent(
                        id=stable_id("ev", clip.upload_id),
                        timestamp=utc_now().isoformat(),
                        event_type="guidance_change",
                        title=f"Guidance discussed in {clip.filename}",
                        description="; ".join(clip.analysis.guidance[:2]),
                        origin="audio",
                        source_ids=[clip.source_id] if clip.source_id else [],
                    )
                )
        for vid in state.get("videos") or []:
            if vid.guidance:
                events.append(
                    TimelineEvent(
                        id=stable_id("ev", vid.upload_id),
                        timestamp=utc_now().isoformat(),
                        event_type="guidance_change",
                        title=f"Guidance presented in {vid.filename}",
                        description="; ".join(vid.guidance[:2]),
                        origin="video",
                        source_ids=[vid.source_id] if vid.source_id else [],
                    )
                )
        if not events:
            raise AgentSkipped("No datable events found")
        events.sort(key=lambda e: e.timestamp)
        events = events[-MAX_EVENTS:]
        return AgentOutput(
            {"events": EventFindings(events=events)}, f"Built a timeline of {len(events)} events"
        )
