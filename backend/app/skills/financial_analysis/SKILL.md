---
name: financial_analysis
purpose: Interpret company fundamentals (SEC XBRL facts, uploaded reports) without fabricating values.
---
# Financial analysis

**When to use:** the Financial Agent, the Document Agent and the Synthesis Agent when fundamentals matter.

**Inputs:** deterministic snapshot (revenue, growth YoY/QoQ, margins, cash, debt, shares), recent filings,
facts extracted from uploaded documents (with page numbers).

**Outputs:** short factual context: scale, growth trend, profitability, balance-sheet strength.

**Rules**
- Every number comes from the snapshot or the document; missing values stay `null` / "not available".
- Growth and margins are already computed in Python — never recompute them.
- Distinguish reported figures (facts) from management guidance (forward-looking) and from your
  interpretation.
- State the period (quarter/annual, period end) whenever citing a figure.

**Limitations:** SEC data covers U.S. registrants only and may lag the latest earnings release by days.
XBRL concept choice (e.g. `Revenues` vs `RevenueFromContract…`) can differ between companies.

References (load only when needed): `references/accounting.md`, `references/valuation.md`.
