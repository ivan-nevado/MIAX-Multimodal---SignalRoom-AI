# Agents

Every agent lives in its own file in `backend/app/agents/`, receives an `AgentContext`
(AI gateway, market/news/financial/macro providers, storage, settings) and returns an
`AgentOutput(update, summary)`. Prompts are in `backend/app/prompts/*.txt`; skills
(concise `SKILL.md` + on-demand `references/`) are in `backend/app/skills/`.

| Agent | Model | What it does | Deterministic part |
|---|---|---|---|
| **Orchestrator** | GPT-6 Luna | Classifies intent (`why_move`, `earnings_review`, `document_review`, `chart_review`, `general_research`) and picks agents. | Hard constraints: attached files must be analysed, minimum team per intent, no SEC for crypto/FX/indices, evidence + synthesis always run. Rule-based fallback without LLM. |
| **Market** | — | Price, 5d/1m returns, volume vs 20d, 20d volatility, 30d drawdown, z-score, anomaly score, benchmark-relative move, intraday bars. | 100 % Python (`analytics/metrics.py`). |
| **News** | GPT-6 Luna (labels) | GDELT + Yahoo (+ Alpha Vantage) → dedupe → rank → cluster → LLM labels each cluster (theme, summary, event type, tone, relevance) from ≤4 headlines. Off-topic clusters dropped. | Retrieval, dedup, ranking, clustering. |
| **Financial** | — | SEC XBRL company facts: revenue, YoY/QoQ growth, margins, cash, debt, shares + recent filings. | 100 % Python (`analytics/financials.py`); missing → `null`. |
| **Macro** | — | S&P 500, Nasdaq, VIX, 10Y yield, dollar, oil, gold (+ FRED Fed funds, CPI YoY, unemployment, GDP, 10Y if key). | 100 % Python. |
| **Document** | GPT-6 Luna + Gemini 3.8 Flash | PDF → text extraction → relevant pages → key facts with page numbers; table/chart-heavy pages rendered and read by Gemini vision. | Page scoring, rendering, page limits. |
| **Vision** | Gemini 3.8 Flash | Chart/table/slide screenshots → image type, observations, levels, uncertainties, hedged interpretation. | Image normalisation (orientation, size, PNG). |
| **Audio** | Gemini 3.8 Flash + GPT-6 Luna | Transcription with language + speaker segmentation → earnings analysis (key points, guidance, tone, risks, quotes). | Quotes kept only if verbatim in the transcript; full transcript stored privately. |
| **Sentiment** | — | Tone level and shift, agreement between sources, `evidence_confidence` (coverage-based, not a probability). | 100 % Python. |
| **Event Detection** | — | Timeline: news clusters, unusual sessions, intraday high/low, SEC filings, guidance in calls. | 100 % Python. |
| **Risk** | GPT-6 Luna | 1–6 risks with LOW/MEDIUM/HIGH and evidence ids from a compact evidence pack. | Unknown ids stripped, unsupported risks dropped; rule-based fallback. |
| **Evidence** | — | Scores likely drivers (formula below) and builds claims (fact / derived metric / interpretation). | 100 % Python (`analytics/scoring.py`). |
| **Synthesis** | GPT-6 Luna | Executive summary, what happened, driver explanations, context, uncertainties, what to watch, claims. | Guardrails: causal softening, advice removal, evidence-id validation, unsupported facts dropped. Deterministic summary if the model is unavailable. |
| **Video** | Gemini 3.8 Flash | One multimodal call reads the speech *and* the slides shown: timestamped transcript by speaker, every slide with its title, description and figures exactly as displayed, key points, guidance, tone, risks. | Quotes kept only if verbatim in the transcript; full transcript stored privately; ≤ 40 MB per video. |
| **Search index** (service, not a graph node) | Gemini Embedding 2 | After each investigation (and follow-ups with new files): passages of summary, drivers, claims, news, PDF facts/pages, call and video transcript windows, video slides, plus uploaded images embedded natively → private index. Powers `/app/search` (text or image query) and retrieval of the top passages for follow-up answers. | Hybrid score (cosine + lexical boost); keyword fallback without the embedding model; per-user, deleted with the investigation. |
| **Voice** | GPT Audio Mini (or Gemini TTS) | Calm, analytical narration of the brief → WAV in S3. | Text made speakable (percentages, signs). |
| **Briefing** | GPT-6 Luna | Daily editorial briefing from watchlist moves, top-mover headlines and market context. | Moves computed in Python; source ids validated. |
| **Research Analyst (follow-up)** | GPT-6 Luna | Answers follow-ups from stored context; runs only the minimal new agents (new files, missing fundamentals/news). | Minimal-work planning rules. |
| **Visual Brief** | Gemini 3.1 Flash Image | Optional infographic of verified findings only (labelled "AI-generated illustration"). | Prompt contains only numbers from the result. |

## Evidence-weighted driver score

```
raw(d) = relevance × source_support × temporal_alignment × sentiment_factor
source_support     = 1 − exp(−independent_publishers / 3)
temporal_alignment = 1 within [−48 h, +36 h] of the session, then exp(−Δh/72), floor 0.2
sentiment_factor   = 1 + 0.25 × alignment   (tone sign agrees with the move)
contribution(d)    = raw(d) / Σ raw × 100   (top 4, drop < 5 %, renormalise)
```

It is a transparent heuristic computed in Python — **not** a probability or a causal model.
The UI labels it "Evidence-weighted contribution".

## Structured output contract

`AIGateway.structured(schema, …)` appends the Pydantic JSON schema to the prompt, requests
JSON mode, validates the answer, retries **once** with a correction prompt, logs failures and
raises `AIResponseError`; the calling agent then degrades gracefully. Malformed JSON is never accepted silently.
