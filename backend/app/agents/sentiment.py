"""Sentiment Agent — tone level, tone shift and agreement between sources (deterministic).

`evidence_confidence` reflects source coverage and agreement — it is NOT a probability.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.analytics.metrics import sentiment_change
from app.analytics.scoring import evidence_confidence
from app.schemas.agents import NewsFindings, SentimentFindings, SeriesPoint

GDELT_TONE_SCALE = 5.0  # GDELT average tone is typically within ±5
TONE_MAP = {"confident": 0.5, "cautious": -0.2, "defensive": -0.5, "mixed": 0.0, "neutral": 0.0}


def daily_tone_series(news: NewsFindings) -> tuple[list[SeriesPoint], str]:
    """Daily tone in [-1, 1]. Prefer GDELT's tone timeline; fall back to labelled cluster tones by day."""
    buckets: dict[str, list[float]] = defaultdict(list)
    if news.tone_timeline:
        for p in news.tone_timeline:
            buckets[p.date[:10]].append(max(-1.0, min(1.0, p.value / GDELT_TONE_SCALE)))
        origin = "GDELT tone timeline"
    else:
        tone_by_article = {aid: c.tone for c in news.clusters if c.tone is not None for aid in c.article_ids}
        for art in news.articles:
            tone = art.tone if art.tone is not None else tone_by_article.get(art.id)
            if tone is not None and art.published_at:
                buckets[art.published_at[:10]].append(tone)
        origin = "headline tone labels"
    series = [SeriesPoint(date=d, value=round(statistics.fmean(v), 3)) for d, v in sorted(buckets.items())]
    return series, origin


def label_for(tone: float | None) -> str:
    if tone is None:
        return "unknown"
    return "positive" if tone > 0.15 else "negative" if tone < -0.15 else "neutral"


class SentimentAgent:
    name = "sentiment"
    label = "Sentiment Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        news: NewsFindings | None = state.get("news")
        audio = state.get("audio") or []
        videos = state.get("videos") or []
        if (news is None or not news.clusters) and not audio and not videos:
            raise AgentSkipped("No news, audio or video to measure sentiment")
        findings = SentimentFindings()
        cluster_tones: list[tuple[float, int]] = []
        publishers: set[str] = set()
        if news is not None:
            series, origin = daily_tone_series(news)
            findings.timeline = series
            recent, prior, change = sentiment_change([p.value for p in series])
            findings.recent_tone = None if recent is None else round(recent, 3)
            findings.prior_tone = None if prior is None else round(prior, 3)
            findings.sentiment_change = None if change is None else round(change, 3)
            for c in news.clusters:
                if c.tone is not None:
                    cluster_tones.append((c.tone, max(c.source_count, 1)))
                    findings.cluster_sentiment.append(
                        {"cluster_id": c.cluster_id, "theme": c.theme, "tone": c.tone}
                    )
            publishers = {a.publisher for a in news.articles}
            findings.confidence_reason = f"Tone from {origin}."
        for clip in audio:
            if clip.analysis is not None:
                cluster_tones.append((TONE_MAP.get(clip.analysis.management_tone, 0.0), 1))
                findings.cluster_sentiment.append(
                    {
                        "cluster_id": clip.source_id,
                        "theme": f"Management tone ({clip.filename})",
                        "tone": TONE_MAP.get(clip.analysis.management_tone, 0.0),
                    }
                )
        for vid in videos:
            tone = TONE_MAP.get(vid.management_tone, 0.0)
            cluster_tones.append((tone, 1))
            findings.cluster_sentiment.append(
                {"cluster_id": vid.source_id, "theme": f"Management tone ({vid.filename})", "tone": tone}
            )

        if cluster_tones:
            total_w = sum(w for _, w in cluster_tones)
            findings.overall_tone = round(sum(t * w for t, w in cluster_tones) / total_w, 3)
        elif findings.recent_tone is not None:
            findings.overall_tone = findings.recent_tone
        findings.label = label_for(findings.overall_tone)  # type: ignore[assignment]

        tones = [t for t, _ in cluster_tones]
        if len(tones) >= 2:
            spread = statistics.pstdev(tones)
            findings.agreement = "aligned" if spread < 0.25 else "mixed" if spread < 0.5 else "divergent"
        elif tones:
            findings.agreement = "aligned"
        level, reason = evidence_confidence(len(publishers), findings.agreement)
        findings.evidence_confidence = level  # type: ignore[assignment]
        findings.confidence_reason = f"{reason} {findings.confidence_reason}".strip()

        shift = ""
        if findings.sentiment_change is not None:
            shift = f", shift {findings.sentiment_change:+.2f}"
        return AgentOutput(
            {"sentiment": findings}, f"Sentiment {findings.label}{shift}; evidence confidence {level}"
        )
