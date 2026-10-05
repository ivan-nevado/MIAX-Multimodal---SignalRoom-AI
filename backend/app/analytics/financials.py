"""Deterministic fundamentals from SEC XBRL company facts (no LLM, never fabricated: missing → None)."""

from __future__ import annotations

from datetime import date
from typing import Any

CONCEPTS: dict[str, list[tuple[str, str]]] = {
    "revenue": [
        ("us-gaap", "Revenues"),
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
        ("us-gaap", "SalesRevenueNet"),
    ],
    "operating_income": [("us-gaap", "OperatingIncomeLoss")],
    "net_income": [("us-gaap", "NetIncomeLoss"), ("us-gaap", "ProfitLoss")],
    "assets": [("us-gaap", "Assets")],
    "liabilities": [("us-gaap", "Liabilities")],
    "cash": [
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    ],
    "debt": [
        ("us-gaap", "LongTermDebt"),
        ("us-gaap", "LongTermDebtNoncurrent"),
        ("us-gaap", "LongTermDebtAndCapitalLeaseObligations"),
    ],
    "shares_outstanding": [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
    ],
}


def _d(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _units(facts: dict[str, Any], taxonomy: str, concept: str) -> list[dict[str, Any]]:
    node = (facts.get("facts", {}).get(taxonomy, {}) or {}).get(concept)
    if not node:
        return []
    units = node.get("units", {})
    for unit in ("USD", "shares"):
        if unit in units:
            items: list[dict[str, Any]] = units[unit]
            return items
    return []


def duration_series(items: list[dict[str, Any]], min_days: int, max_days: int) -> list[tuple[date, float]]:
    """Facts covering a period of min..max days, one value per period end (latest filing wins)."""
    best: dict[date, tuple[str, float]] = {}
    for it in items:
        start, end = _d(it.get("start")), _d(it.get("end"))
        if not start or not end or it.get("val") is None:
            continue
        span = (end - start).days
        if not (min_days <= span <= max_days):
            continue
        filed = it.get("filed") or ""
        if end not in best or filed > best[end][0]:
            best[end] = (filed, float(it["val"]))
    return sorted((end, val) for end, (_, val) in best.items())


def instant_series(items: list[dict[str, Any]]) -> list[tuple[date, float]]:
    best: dict[date, tuple[str, float]] = {}
    for it in items:
        end = _d(it.get("end"))
        if not end or it.get("val") is None or it.get("start"):
            continue
        filed = it.get("filed") or ""
        if end not in best or filed > best[end][0]:
            best[end] = (filed, float(it["val"]))
    return sorted((end, val) for end, (_, val) in best.items())


def value_near(series: list[tuple[date, float]], target: date, tolerance_days: int = 25) -> float | None:
    candidates = [
        (abs((end - target).days), val) for end, val in series if abs((end - target).days) <= tolerance_days
    ]
    return min(candidates)[1] if candidates else None


def growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round((current - prior) / abs(prior), 4)


def margin(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 4)


def first_available(facts: dict[str, Any], key: str, kind: str) -> list[tuple[date, float]]:
    for taxonomy, concept in CONCEPTS[key]:
        items = _units(facts, taxonomy, concept)
        if not items:
            continue
        if kind == "quarter":
            series = duration_series(items, 80, 100)
        elif kind == "annual":
            series = duration_series(items, 350, 380)
        else:
            series = instant_series(items)
        if series:
            return series
    return []


def snapshot_from_companyfacts(facts: dict[str, Any]) -> dict[str, Any]:
    """Latest-quarter fundamentals with YoY / QoQ growth and margins."""
    out: dict[str, Any] = {"entity_name": facts.get("entityName")}
    revenue_q = first_available(facts, "revenue", "quarter")
    op_q = first_available(facts, "operating_income", "quarter")
    net_q = first_available(facts, "net_income", "quarter")

    if revenue_q:
        last_end, last_rev = revenue_q[-1]
        out["period_end"] = last_end.isoformat()
        out["fiscal_period"] = "quarter"
        out["revenue"] = last_rev
        prior_year = value_near(revenue_q, last_end.replace(year=last_end.year - 1))
        out["revenue_growth_yoy"] = growth(last_rev, prior_year)
        out["revenue_growth_qoq"] = growth(last_rev, revenue_q[-2][1]) if len(revenue_q) > 1 else None
        op = value_near(op_q, last_end, 5)
        net = value_near(net_q, last_end, 5)
        out["operating_income"] = op
        out["net_income"] = net
        out["operating_margin"] = margin(op, last_rev)
        out["net_margin"] = margin(net, last_rev)
    else:
        revenue_a = first_available(facts, "revenue", "annual")
        if revenue_a:
            last_end, last_rev = revenue_a[-1]
            out["period_end"] = last_end.isoformat()
            out["fiscal_period"] = "annual"
            out["revenue"] = last_rev
            out["revenue_growth_yoy"] = growth(last_rev, revenue_a[-2][1]) if len(revenue_a) > 1 else None
            op = value_near(first_available(facts, "operating_income", "annual"), last_end, 5)
            net = value_near(first_available(facts, "net_income", "annual"), last_end, 5)
            out["operating_income"], out["net_income"] = op, net
            out["operating_margin"], out["net_margin"] = margin(op, last_rev), margin(net, last_rev)

    for key in ("assets", "liabilities", "cash", "debt", "shares_outstanding"):
        series = first_available(facts, key, "instant")
        out[key] = series[-1][1] if series else None
    return out
