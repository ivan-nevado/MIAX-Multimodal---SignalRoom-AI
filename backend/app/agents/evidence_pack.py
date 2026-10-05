"""Compact, id-addressable evidence pack shared by the Risk, Synthesis and Follow-up agents.

Only these ids may be cited by a model; anything else is stripped by the guardrails.
"""

from __future__ import annotations

from typing import Any


def _fmt(value: float | None, pct: bool = False, money: bool = False) -> str:
    if value is None:
        return "n/a"
    if pct:
        return f"{value * 100:.1f}%"
    if money:
        for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
            if abs(value) >= div:
                return f"${value / div:.2f}{unit}"
        return f"${value:,.0f}"
    return f"{value:,.2f}"


def build_evidence_pack(state: dict[str, Any], max_news: int = 6) -> list[dict[str, Any]]:
    pack: list[dict[str, Any]] = []
    market = state.get("market")
    if market is not None:
        m = market.metrics
        pack.append(
            {
                "id": market.source_ids[0] if market.source_ids else "market",
                "type": "market_metrics",
                "facts": {
                    "symbol": m.symbol,
                    "as_of": m.as_of,
                    "last_price": m.last_price,
                    "currency": m.currency,
                    "move_pct": m.move_pct,
                    "return_5d_pct": m.return_5d_pct,
                    "return_1m_pct": m.return_1m_pct,
                    "volume_change_pct": m.volume_change_pct,
                    "volatility_20d_annualized": m.volatility_20d,
                    "drawdown_30d_pct": m.drawdown_30d,
                    "zscore_move": m.zscore_move,
                    "anomaly_score": m.anomaly_score,
                    "unusual_move": m.unusual_move,
                    "benchmark": m.benchmark_symbol,
                    "benchmark_move_pct": m.benchmark_move_pct,
                    "relative_performance_pp": m.relative_performance_pct,
                },
                "observations": m.observations,
            }
        )
    news = state.get("news")
    if news is not None:
        by_id = {a.id: a for a in news.articles}
        for c in news.clusters[:max_news]:
            pack.append(
                {
                    "id": c.cluster_id,
                    "type": "news_cluster",
                    "theme": c.theme,
                    "summary": c.summary,
                    "event_type": c.event_type,
                    "tone": c.tone,
                    "independent_publishers": c.source_count,
                    "first_seen": c.first_seen,
                    "articles": [
                        {"source_id": a, "title": by_id[a].title, "publisher": by_id[a].publisher}
                        for a in c.article_ids[:3]
                        if a in by_id
                    ],
                }
            )
    fin = state.get("financial")
    if fin is not None and fin.applicable and fin.source_ids:
        pack.append(
            {
                "id": fin.source_ids[0],
                "type": "fundamentals",
                "facts": {
                    "entity": fin.entity_name,
                    "period": fin.fiscal_period,
                    "period_end": fin.period_end,
                    "revenue": _fmt(fin.revenue, money=True),
                    "revenue_growth_yoy": _fmt(fin.revenue_growth_yoy, pct=True),
                    "revenue_growth_qoq": _fmt(fin.revenue_growth_qoq, pct=True),
                    "operating_margin": _fmt(fin.operating_margin, pct=True),
                    "net_margin": _fmt(fin.net_margin, pct=True),
                    "cash": _fmt(fin.cash, money=True),
                    "debt": _fmt(fin.debt, money=True),
                },
                "recent_filings": [f"{f.form} {f.filed}" for f in fin.recent_filings[:4]],
            }
        )
    macro = state.get("macro")
    if macro is not None:
        pack.append(
            {
                "id": "macro_context",
                "type": "macro",
                "indicators": [
                    {
                        "source_id": i.source_id,
                        "name": i.name,
                        "value": i.value,
                        "change": i.change,
                        "unit": i.unit,
                    }
                    for i in macro.indicators[:8]
                ],
            }
        )
    for doc in state.get("documents") or []:
        pack.append(
            {
                "id": doc.source_id,
                "type": "uploaded_document",
                "filename": doc.filename,
                "summary": doc.summary,
                "key_facts": [f"{f.fact}: {f.value} (p.{f.page})" for f in doc.key_facts[:10]],
                "risks": doc.risks[:6],
                "guidance": doc.guidance[:4],
            }
        )
    for img in state.get("images") or []:
        pack.append(
            {
                "id": img.source_id,
                "type": "uploaded_image",
                "image_type": img.image_type,
                "observations": img.observations[:6],
                "uncertainties": img.uncertainties[:4],
                "interpretation": img.interpretation,
            }
        )
    for clip in state.get("audio") or []:
        item: dict[str, Any] = {"id": clip.source_id, "type": "uploaded_audio", "filename": clip.filename}
        if clip.analysis:
            item.update(
                {
                    "summary": clip.analysis.summary,
                    "key_points": clip.analysis.key_points[:6],
                    "guidance": clip.analysis.guidance[:4],
                    "management_tone": clip.analysis.management_tone,
                    "risks": clip.analysis.risks[:5],
                    "quotes": clip.analysis.notable_quotes,
                }
            )
        pack.append(item)
    for vid in state.get("videos") or []:
        pack.append(
            {
                "id": vid.source_id,
                "type": "uploaded_video",
                "filename": vid.filename,
                "summary": vid.summary,
                "key_points": vid.key_points[:6],
                "guidance": vid.guidance[:4],
                "management_tone": vid.management_tone,
                "risks": vid.risks[:5],
                "quotes": vid.notable_quotes,
                "slides": [
                    {"t": s.timestamp, "title": s.title, "figures": [f.model_dump() for f in s.figures[:6]]}
                    for s in vid.slides[:8]
                ],
            }
        )
    sentiment = state.get("sentiment")
    if sentiment is not None:
        pack.append(
            {
                "id": "sentiment",
                "type": "sentiment",
                "label": sentiment.label,
                "overall_tone": sentiment.overall_tone,
                "sentiment_change": sentiment.sentiment_change,
                "agreement": sentiment.agreement,
                "evidence_confidence": sentiment.evidence_confidence,
            }
        )
    return pack


def known_evidence_ids(state: dict[str, Any]) -> set[str]:
    ids = {s.id for s in state.get("sources") or []}
    news = state.get("news")
    if news is not None:
        ids |= {c.cluster_id for c in news.clusters}
    return ids
