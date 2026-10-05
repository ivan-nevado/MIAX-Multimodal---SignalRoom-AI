# Demo script (3–5 minutes)

Before the demo: run `./scripts/seed_demo.sh` (local) or sign up on the cloud URL, and keep
`demo_data/earnings_call.wav` and `demo_data/northwind_q3_fy2026_results.pdf` at hand.

1. **Landing page** (`/`) — tagline, the AI research team, multimodal flow, "Why?" example, pricing, disclaimer.
2. **Sign in** — Cognito in AWS (email verification + forgot password) or local auth.
3. **Dashboard** — market overview, watchlist with **Why?**, largest moves, daily briefing with audio, recent investigations.
4. **Select NVIDIA** → asset page: candlesticks + volume (1D/1W/1M/1Y), news, SEC snapshot.
5. Click **Investigate why**.
6. **Real agent progress** — "SignalRoom is assembling your research team…", agents tick off live via SSE
   (Orchestrator → Market, News, Financial, Macro in parallel → Sentiment, Events → Risk → Evidence → Synthesis → Voice).
7. **Final explanation** — what happened, likely drivers with *evidence-weighted contribution*, what to watch, uncertainty.
8. **Evidence graph** — move → drivers → sources; click a source to open publisher, date and link.
9. **Market tab** — price chart, intraday, relative performance vs S&P 500, sentiment timeline, event timeline, macro.
10. **Research** → attach `earnings_call.wav` (+ the PDF) → "Summarize this earnings call and identify the most important risks."
11. **Documents & media tab** — transcript with speakers (Gemini), key points, guidance, verbatim quotes, PDF facts with page numbers and the table read by vision.
11b. Run a second research with `northwind_webinar.mp4` (results webinar) → **Video card**: slides with timestamps and the figures exactly as shown (e.g. Q4 guidance $4.0–4.2B at 01:20), transcript, tone and verified quotes.
11c. **Search** (sidebar) → "what did the CFO say about gross margin" → the exact transcript passage (with its timestamp) ranks first, across every investigation. Then **Search by image** with `nvda_chart.png`.
12. Ask the follow-up: **"Does this change the thesis?"** — answered from stored context, citing evidence.
13. Show the **updated answer** and the risk matrix.
14. Click **Listen** — narrated brief (GPT Audio TTS). Optionally **Create visual brief** (image model).
15. **Briefings** → generated briefing with audio player.
16. **Email preview** — the HTML email exactly as sent through SES.

Point out on the way: model usage & cost panel (multi-model orchestration is visible), "Market data may be delayed",
and that every number comes from deterministic code while models only interpret.

No backend available? `VITE_DEMO_MODE=true` replays recorded real runs of all of the above.
