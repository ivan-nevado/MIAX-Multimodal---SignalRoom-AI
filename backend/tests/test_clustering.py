from __future__ import annotations

from datetime import timedelta

from app.analytics.clustering import (
    cluster_articles,
    deduplicate,
    jaccard,
    normalize_url,
    rank_articles,
    tokenize,
)
from app.schemas.agents import NewsArticle
from tests.fakes import NOW, make_articles


def test_tokenize_and_jaccard() -> None:
    toks = tokenize("NVIDIA shares fall on U.S. export rules")
    assert "export" in toks and "the" not in toks
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard(set(), {"a"}) == 0.0


def test_normalize_url_strips_tracking() -> None:
    assert normalize_url("https://www.Reuters.com/a/b/?utm=1#x") == "reuters.com/a/b"


def test_deduplicate_removes_url_and_headline_duplicates() -> None:
    arts = make_articles()
    near = arts[1].model_copy(update={"id": "near", "url": "https://other.com/x"})  # syndicated copy
    deduped = deduplicate([*arts, near])
    ids = {a.id for a in deduped}
    assert "fk_dup" not in ids
    assert "near" not in ids
    assert len(deduped) == len(arts) - 1  # only the exact duplicate goes; distinct headlines stay


def test_rank_prefers_entity_mention_and_recency() -> None:
    fresh = NewsArticle(
        id="a",
        title="NVIDIA earnings beat",
        url="https://x.com/a",
        publisher="x",
        published_at=NOW.isoformat(),
        retrieved_at=NOW.isoformat(),
        provider="t",
    )
    stale = fresh.model_copy(
        update={"id": "b", "title": "Markets drift", "published_at": (NOW - timedelta(days=6)).isoformat()}
    )
    ranked = rank_articles([stale, fresh], ["NVIDIA"], NOW)
    assert ranked[0].id == "a"
    assert ranked[0].relevance > ranked[1].relevance


def test_cluster_groups_related_headlines() -> None:
    arts = rank_articles(deduplicate(make_articles()), ["NVIDIA", "NVDA"], NOW)
    clusters = cluster_articles(arts, ["NVIDIA", "NVDA"])
    assert len(clusters) == 3
    top = clusters[0]
    assert top.source_count == 5  # the export story has 5 independent publishers
    assert top.first_seen is not None
    assert sum(len(c.article_ids) for c in clusters) == len(arts)
