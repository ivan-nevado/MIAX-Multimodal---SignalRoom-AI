# Data sources

SignalRoom depends only on free (or free-for-education) data. Every adapter sits behind an
interface (`MarketDataProvider`, `NewsProvider`, `FinancialDataProvider`, `MacroDataProvider`)
and every external datum records `source`, `retrieved_at` and `published_at` when available.

| Source | Key? | Used for | Adapter | Cache TTL |
|---|---|---|---|---|
| **Yahoo Finance via `yfinance`** | No | OHLCV history (1D/5D/1M/6M/1Y), quotes, ticker search, cross-asset context | `integrations/market/yahoo.py` | quote 60 s, intraday 2 min, daily 15 min, profile/search 24 h |
| **Yahoo Finance news (via yfinance search)** | No | Recent headlines (metadata + link only) | `integrations/news/yahoo.py` | 10 min |
| **GDELT DOC 2.0** | No | Global article discovery, tone & volume timelines | `integrations/news/gdelt.py` | 10 min |
| **SEC EDGAR** (`company_tickers.json`, `companyfacts`, `submissions`) | No (descriptive User-Agent required) | Fundamentals, filings | `integrations/financial/sec.py` | 12–24 h |
| **Alpha Vantage** | Free key (optional) | Fallback daily prices, NEWS_SENTIMENT with per-ticker scores | `integrations/market/alpha_vantage.py`, `integrations/news/alpha_vantage.py` | 10–15 min |
| **FRED** | Free key (optional) | Fed funds, CPI YoY, unemployment, real GDP growth, 10Y | `integrations/macro/fred.py` | 6 h |

## Important notes

* **yfinance** is an unofficial open-source interface intended for personal/research use. SignalRoom treats it as an
  academic prototype source; the UI always shows "Market data may be delayed. Educational prototype."
* **GDELT** asks for ≤1 request every 5 s. All requests share a process-wide rate limiter, use retries with backoff
  and a **circuit breaker**: after repeated 429s or timeouts GDELT is skipped for 2 minutes and Yahoo / Alpha
  Vantage keep serving news. From some networks GDELT rate-limits aggressively; the product still works.
* **SEC**: requests send a descriptive `User-Agent` (`SEC_USER_AGENT`), stay far below 10 req/s and are cached.
* **Alpha Vantage** free tier is small (≈25 requests/day) and only free endpoints are used. Its absence never breaks
  the app. Alpha Vantage also offers free keys for verified open-source/educational projects.
* Article bodies are **not** scraped; only headline metadata and links to the original publisher are stored.
* Cache keys always contain `provider:kind:asset:query:window` (DynamoDB `cache` table with TTL in AWS,
  in-memory locally), so one investigation never calls the same source twice.

## Entity resolution

`services/entity_resolution.py` resolves names deterministically before any provider search:
NVIDIA → NVDA, Tesla → TSLA, Bitcoin → BTC-USD, S&P 500 → ^GSPC, EUR/USD → EURUSD=X, gold → GC=F, etc.
Unknown names fall back to Yahoo search results the user selects. The LLM is never used for ticker resolution.
