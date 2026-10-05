---
name: news_research
purpose: Turn clustered headlines into neutral, sourced themes.
---
# News research

**When to use:** News Agent cluster labelling, Event Detection, Briefing.

**Pipeline (deterministic before any LLM call):** query → retrieve (GDELT, Yahoo Finance, optional
Alpha Vantage) → deduplicate (URL + headline similarity) → rank (entity mention, recency, finance
keywords) → cluster (headline token overlap) → **LLM labels clusters** (only 3-4 headlines per cluster).

**Rules**
- Summarise what headlines report, never what you believe happened.
- Never invent publishers, URLs, quotes or numbers. Links always point to the original publisher.
- Generic market commentary that only mentions the asset gets low relevance.
- Use event types: earnings, guidance_change, regulation, lawsuit, management_change, m_and_a, product,
  analyst_action, macro, sector_move, market_move, filing, other.

**Limitations:** headlines only (no article bodies); GDELT is rate limited (1 request / 5 s).

References: `references/source-quality.md`.
