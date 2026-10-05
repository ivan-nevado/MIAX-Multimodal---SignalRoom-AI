"""Official SEC EDGAR APIs (keyless). Polite usage: descriptive User-Agent, caching, few requests.

Endpoints:
  https://www.sec.gov/files/company_tickers.json            ticker → CIK
  https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json   XBRL facts
  https://data.sec.gov/submissions/CIK##########.json        filing metadata
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import httpx

from app.analytics.financials import snapshot_from_companyfacts
from app.integrations.cache import TTL_SEC_FACTS, TTL_SEC_TICKERS, cache_key, cached
from app.integrations.financial.base import FinancialDataError
from app.repositories.base import CacheRepository
from app.schemas.agents import Filing, FinancialSnapshot

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
RELEVANT_FORMS = {"10-K", "10-Q", "8-K", "20-F", "6-K", "DEF 14A", "S-1", "10-K/A", "10-Q/A"}

_ticker_map: dict[str, tuple[str, str]] = {}


class SecFinancialDataProvider:
    name = "sec_edgar"

    def __init__(
        self,
        user_agent: str,
        cache: CacheRepository | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not user_agent:
            raise ValueError("SEC requires a descriptive User-Agent")
        self._headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self._cache = cache
        self._transport = transport

    async def _get_json(self, url: str) -> dict[str, Any]:
        # A handful of requests per investigation (cached): far below SEC's 10 req/s guidance.
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30, transport=self._transport) as client:
                    resp = await client.get(url, headers=self._headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < 2:
                    await asyncio.sleep(1 + attempt)
                    continue
                raise FinancialDataError(f"SEC unreachable: {type(exc).__name__}") from exc
            if resp.status_code == 404:
                raise FinancialDataError("SEC: no data for this company")
            if resp.status_code in (429, 503) and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise FinancialDataError(f"SEC HTTP {resp.status_code}")
            data: dict[str, Any] = resp.json()
            return data
        raise FinancialDataError("SEC request failed")

    async def resolve_cik(self, symbol: str) -> tuple[str, str] | None:
        global _ticker_map
        if not _ticker_map:

            async def load() -> dict[str, list[str]]:
                raw = await self._get_json(TICKERS_URL)
                return {v["ticker"].upper(): [str(v["cik_str"]).zfill(10), v["title"]] for v in raw.values()}

            mapping = await cached(self._cache, cache_key(self.name, "tickers"), TTL_SEC_TICKERS, load)
            _ticker_map = {k: (v[0], v[1]) for k, v in mapping.items()}
        return _ticker_map.get(symbol.upper().replace(".", "-"))

    async def recent_filings(self, cik: str, limit: int = 8) -> list[Filing]:
        async def load() -> list[dict[str, Any]]:
            data = await self._get_json(SUBMISSIONS_URL.format(cik=cik))
            recent = data.get("filings", {}).get("recent", {})
            rows = []
            for i, form in enumerate(recent.get("form", [])):
                if form not in RELEVANT_FORMS:
                    continue
                accession = recent["accessionNumber"][i].replace("-", "")
                doc = recent.get("primaryDocument", [""] * (i + 1))[i]
                rows.append(
                    {
                        "form": form,
                        "filed": recent["filingDate"][i],
                        "description": (recent.get("primaryDocDescription") or [None] * (i + 1))[i] or form,
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
                        if doc
                        else None,
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        rows = await cached(self._cache, cache_key(self.name, "submissions", cik), TTL_SEC_FACTS, load)
        return [Filing.model_validate(r) for r in rows]

    async def snapshot(self, symbol: str) -> FinancialSnapshot:
        if symbol.startswith("^") or "=" in symbol or symbol.endswith("-USD"):
            return FinancialSnapshot(
                applicable=False, note="SEC fundamentals apply to U.S.-listed companies only."
            )
        resolved = await self.resolve_cik(symbol)
        if not resolved:
            return FinancialSnapshot(
                applicable=False, note=f"{symbol} is not an SEC registrant (no CIK found)."
            )
        cik, title = resolved

        async def load() -> dict[str, Any]:
            facts = await self._get_json(FACTS_URL.format(cik=cik))
            return snapshot_from_companyfacts(facts)

        try:
            values = await cached(self._cache, cache_key(self.name, "facts", cik), TTL_SEC_FACTS, load)
        except FinancialDataError as exc:
            logger.info("sec_facts_unavailable", extra={"symbol": symbol, "error": str(exc)})
            values = {"entity_name": title}
        filings: list[Filing] = []
        with contextlib.suppress(FinancialDataError):
            filings = await self.recent_filings(cik)
        snap = FinancialSnapshot(
            cik=cik,
            recent_filings=filings,
            **{k: v for k, v in values.items() if k in FinancialSnapshot.model_fields},
        )
        snap.entity_name = snap.entity_name or title
        return snap
