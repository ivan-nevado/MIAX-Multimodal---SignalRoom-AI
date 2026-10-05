"""Deterministic news pipeline: deduplicate → rank → cluster.

Only the compact cluster representation (a few headlines per cluster) is ever
sent to an LLM, never dozens of raw articles.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from datetime import datetime

from app.schemas.agents import NewsArticle, NewsCluster
from app.utils.ids import stable_id
from app.utils.time import parse_iso, utc_now

_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "at",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "after",
        "before",
        "over",
        "under",
        "into",
        "about",
        "amid",
        "than",
        "then",
        "so",
        "but",
        "not",
        "no",
        "new",
        "says",
        "said",
        "say",
        "stock",
        "stocks",
        "shares",
        "share",
        "inc",
        "corp",
        "corporation",
        "company",
        "co",
        "ltd",
        "plc",
        "today",
        "week",
        "why",
        "how",
        "what",
        "will",
        "could",
        "would",
        "may",
        "might",
        "up",
        "down",
        "us",
        "u.s",
        "vs",
        "via",
        "report",
        "reports",
        "news",
        "update",
        "live",
        "market",
        "markets",
    ]
)
_FINANCE_KEYWORDS = frozenset(
    [
        "earnings",
        "revenue",
        "guidance",
        "profit",
        "loss",
        "forecast",
        "outlook",
        "downgrade",
        "upgrade",
        "analyst",
        "sec",
        "regulator",
        "regulation",
        "export",
        "ban",
        "lawsuit",
        "probe",
        "investigation",
        "acquisition",
        "merger",
        "deal",
        "ceo",
        "cfo",
        "resign",
        "tariff",
        "rate",
        "fed",
        "inflation",
        "chip",
        "demand",
        "sales",
        "margin",
        "dividend",
        "buyback",
        "layoffs",
        "recall",
        "approval",
    ]
)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-\.&]*")


def tokenize(text: str, exclude: frozenset[str] = frozenset()) -> set[str]:
    tokens = {_stem(t.strip(".-")) for t in _TOKEN_RE.findall(text.lower())}
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS and t not in exclude}


def _stem(token: str) -> str:
    """Very light stemming so 'rules'/'rule' or 'chips'/'chip' match across headlines."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def overlap(a: set[str], b: set[str]) -> float:
    """Overlap coefficient: better than Jaccard for short headlines of different lengths."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalize_url(url: str) -> str:
    url = url.strip().lower().split("#")[0].split("?")[0]
    return url.rstrip("/").replace("https://", "").replace("http://", "").replace("www.", "")


def deduplicate(articles: Sequence[NewsArticle], title_threshold: float = 0.8) -> list[NewsArticle]:
    """Drop exact URL duplicates and near-identical headlines (syndicated copies)."""
    seen_urls: set[str] = set()
    kept: list[NewsArticle] = []
    kept_tokens: list[set[str]] = []
    for art in articles:
        key = normalize_url(art.url)
        if key in seen_urls:
            continue
        toks = tokenize(art.title)
        if any(jaccard(toks, other) >= title_threshold for other in kept_tokens):
            continue
        seen_urls.add(key)
        kept.append(art)
        kept_tokens.append(toks)
    return kept


def score_relevance(
    article: NewsArticle, entity_terms: Sequence[str], reference_time: datetime | None = None
) -> float:
    """0-1 relevance: entity mention in headline (50%), recency (30%), finance keywords (20%)."""
    title = article.title.lower()
    mention = 1.0 if any(term.lower() in title for term in entity_terms if term) else 0.0
    ref = reference_time or utc_now()
    published = parse_iso(article.published_at)
    if published is None:
        recency = 0.4
    else:
        age_hours = max((ref - published).total_seconds() / 3600.0, 0.0)
        recency = math.exp(-age_hours / 72.0)
    keyword = 1.0 if tokenize(article.title) & _FINANCE_KEYWORDS else 0.0
    return round(0.5 * mention + 0.3 * recency + 0.2 * keyword, 3)


def rank_articles(
    articles: Sequence[NewsArticle], entity_terms: Sequence[str], reference_time: datetime | None = None
) -> list[NewsArticle]:
    ranked = []
    for art in articles:
        ranked.append(
            art.model_copy(update={"relevance": score_relevance(art, entity_terms, reference_time)})
        )
    ranked.sort(key=lambda a: (a.relevance, a.published_at or ""), reverse=True)
    return ranked


def headline_similarity(a: set[str], b: set[str]) -> float:
    """Similarity used for clustering: overlap coefficient, but only if ≥2 informative tokens are shared."""
    return overlap(a, b) if len(a & b) >= 2 else 0.0


def cluster_articles(
    articles: Sequence[NewsArticle],
    entity_terms: Sequence[str] = (),
    threshold: float = 0.3,
    max_clusters: int = 6,
) -> list[NewsCluster]:
    """Greedy single-link clustering on headline tokens (entity names excluded so they don't dominate)."""
    exclude = frozenset(t for term in entity_terms for t in tokenize(term))
    groups: list[list[tuple[NewsArticle, set[str]]]] = []
    for art in articles:
        toks = tokenize(art.title, exclude)
        best_idx, best_sim = -1, 0.0
        for idx, group in enumerate(groups):
            sim = max(headline_similarity(toks, other) for _, other in group)
            if sim > best_sim:
                best_idx, best_sim = idx, sim
        if best_idx >= 0 and best_sim >= threshold:
            groups[best_idx].append((art, toks))
        else:
            groups.append([(art, toks)])

    clusters: list[NewsCluster] = []
    for group in groups:
        arts = [a for a, _ in group]
        publishers = {a.publisher for a in arts}
        avg_rel = sum(a.relevance for a in arts) / len(arts)
        times = sorted(a.published_at for a in arts if a.published_at)
        # Provisional theme = most common informative tokens; the News Agent's LLM step relabels it.
        counts: dict[str, int] = {}
        for _, toks in group:
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
        top_tokens = [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
        clusters.append(
            NewsCluster(
                cluster_id=stable_id("cl", *sorted(a.id for a in arts)),
                theme=" / ".join(top_tokens) or arts[0].title[:60],
                summary="",
                relevance=round(min(avg_rel, 1.0), 3),
                article_ids=[a.id for a in arts],
                first_seen=times[0] if times else None,
                source_count=len(publishers),
            )
        )
    # Rank by evidence mass: independent publishers × relevance.
    clusters.sort(key=lambda c: (c.source_count * c.relevance, c.relevance), reverse=True)
    return clusters[:max_clusters]
