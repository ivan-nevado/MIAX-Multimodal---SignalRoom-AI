from __future__ import annotations

import pytest

from app.agents.guardrails import clean_narrative, filter_ids, soften_causality, strip_advice, verbatim_quotes
from app.analytics.financials import growth, margin, snapshot_from_companyfacts


def _q(start: str, end: str, val: float, filed: str = "2026-01-01") -> dict[str, object]:
    return {"start": start, "end": end, "val": val, "filed": filed, "form": "10-Q"}


FACTS = {
    "entityName": "TEST CORP",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        _q("2025-04-01", "2025-06-30", 100.0),
                        _q("2025-07-01", "2025-09-30", 110.0),
                        _q("2026-04-01", "2026-06-30", 150.0),
                        _q(
                            "2026-04-01", "2026-06-30", 151.0, filed="2026-08-01"
                        ),  # restated: latest filing wins
                        _q(
                            "2025-07-01", "2026-06-30", 999.0
                        ),  # annual-length fact must be ignored for quarters
                    ]
                }
            },
            "OperatingIncomeLoss": {"units": {"USD": [_q("2026-04-01", "2026-06-30", 60.4)]}},
            "NetIncomeLoss": {"units": {"USD": [_q("2026-04-01", "2026-06-30", 45.3)]}},
            "CashAndCashEquivalentsAtCarryingValue": {
                "units": {"USD": [{"end": "2026-06-30", "val": 30.0, "filed": "2026-08-01"}]}
            },
            "LongTermDebt": {"units": {"USD": [{"end": "2026-06-30", "val": 12.0, "filed": "2026-08-01"}]}},
        }
    },
}


def test_snapshot_from_companyfacts_quarter() -> None:
    snap = snapshot_from_companyfacts(FACTS)
    assert snap["entity_name"] == "TEST CORP"
    assert snap["revenue"] == 151.0
    assert snap["period_end"] == "2026-06-30"
    assert snap["revenue_growth_yoy"] == pytest.approx(0.51)
    assert snap["operating_margin"] == pytest.approx(0.4, abs=1e-3)
    assert snap["net_margin"] == pytest.approx(0.3, abs=1e-3)
    assert snap["cash"] == 30.0 and snap["debt"] == 12.0
    assert snap["assets"] is None  # never fabricated


def test_snapshot_missing_everything() -> None:
    snap = snapshot_from_companyfacts({"entityName": "EMPTY", "facts": {}})
    assert snap.get("revenue") is None and snap["cash"] is None


def test_growth_and_margin_guards() -> None:
    assert growth(110, 100) == pytest.approx(0.1)
    assert growth(1, 0) is None and growth(None, 1) is None
    assert margin(1, 0) is None and margin(25, 100) == 0.25


def test_guardrails_soften_and_strip() -> None:
    assert "likely drove" in soften_causality("Export news caused the stock to fall.")
    assert "was likely driven by" in soften_causality("The fall was caused by export rules.")
    assert soften_causality("It likely caused") == "It likely caused"
    cleaned = clean_narrative("Shares fell 6%. You should buy the dip now. Volume spiked.")
    assert "buy" not in cleaned.lower() and "Volume spiked." in cleaned
    assert strip_advice("We recommend selling.") == ""


def test_filter_ids_and_verbatim_quotes() -> None:
    assert filter_ids(["a", "x", "a", "b"], {"a", "b"}) == ["a", "b"]
    transcript = "CEO: Revenue grew 31 percent this quarter.\nCFO: Margins fell."
    assert verbatim_quotes(['"Revenue grew 31 percent"', "Margins doubled"], transcript) == [
        "Revenue grew 31 percent"
    ]
