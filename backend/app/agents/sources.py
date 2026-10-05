"""Builders for Source objects. URLs/publishers always come from provider data."""

from __future__ import annotations

from urllib.parse import quote

from app.schemas.agents import Filing, MacroIndicator, NewsArticle
from app.schemas.common import Source
from app.utils.ids import stable_id
from app.utils.time import utc_now_iso


def market_source(symbol: str, provider: str, title: str | None = None) -> Source:
    return Source(
        id=f"src_mkt_{symbol.lower().replace('^', '').replace('=', '').replace('.', '').replace('-', '')}",
        title=title or f"{symbol} price & volume history",
        publisher="Yahoo Finance" if "yahoo" in provider else provider,
        url=f"https://finance.yahoo.com/quote/{quote(symbol)}",
        retrieved_at=utc_now_iso(),
        source_type="market_data",
        relevance=1.0,
        provider=provider,
    )


def news_source(article: NewsArticle) -> Source:
    return Source(
        id=article.id,
        title=article.title,
        publisher=article.publisher,
        url=article.url,
        published_at=article.published_at,
        retrieved_at=article.retrieved_at,
        source_type="news",
        relevance=article.relevance,
        provider=article.provider,
    )


def sec_facts_source(cik: str, entity: str | None) -> Source:
    return Source(
        id=f"src_sec_facts_{cik}",
        title=f"SEC XBRL company facts — {entity or cik}",
        publisher="SEC EDGAR",
        url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
        retrieved_at=utc_now_iso(),
        source_type="financial_data",
        relevance=0.9,
        provider="sec_edgar",
    )


def filing_source(cik: str, filing: Filing) -> Source:
    return Source(
        id=stable_id("src_filing", cik, filing.form, filing.filed),
        title=f"{filing.form} filed {filing.filed}"
        + (f" — {filing.description}" if filing.description and filing.description != filing.form else ""),
        publisher="SEC EDGAR",
        url=filing.url,
        published_at=filing.filed,
        retrieved_at=utc_now_iso(),
        source_type="sec_filing",
        relevance=0.7,
        provider="sec_edgar",
    )


def macro_source(indicator: MacroIndicator) -> Source:
    is_fred = indicator.provider == "fred"
    return Source(
        id=indicator.source_id or f"src_macro_{indicator.id.lower()}",
        title=f"{indicator.name} ({indicator.id})",
        publisher="FRED, Federal Reserve Bank of St. Louis" if is_fred else "Yahoo Finance",
        url=f"https://fred.stlouisfed.org/series/{indicator.id}"
        if is_fred
        else f"https://finance.yahoo.com/quote/{quote(indicator.id)}",
        published_at=indicator.as_of,
        retrieved_at=utc_now_iso(),
        source_type="macro",
        relevance=0.5,
        provider=indicator.provider,
    )


def upload_source(kind: str, upload_id: str, filename: str) -> Source:
    source_type = {"document": "document", "image": "image", "audio": "audio", "video": "video"}[kind]
    return Source(
        id=f"src_{kind}_{upload_id}",
        title=filename,
        publisher="Your upload",
        url=None,
        retrieved_at=utc_now_iso(),
        source_type=source_type,
        relevance=0.9,
        provider="user_upload",
    )
