# Compliance, privacy & responsible AI

SignalRoom is an **educational prototype**. It is not a regulated investment service and makes no claim of
regulatory certification.

## Financial regulation posture
* No personalised investment advice, no buy/sell/hold recommendations (prompts forbid it; a guardrail strips
  advice sentences such as "you should buy").
* No order execution, brokerage or payments.
* Causality is never asserted without a source: "caused" is softened to "likely drove"; drivers are "likely drivers";
  driver percentages are labelled "evidence-weighted contribution" (a heuristic, not a probability).
* Disclaimer visible on the landing page, app footer, investigation page, briefings, emails and Settings.
* In a real launch: MiFID II / CNMV analysis of whether the product constitutes investment advice or research,
  ESMA guidance on AI in investment services, EU AI Act transparency obligations (users are told content is AI-generated).

## Data protection (GDPR-oriented design)
* Data minimisation: email + preferences only; no banking data, no portfolio holdings.
* Uploaded files: private S3 (SSE, TLS-only policy, presigned URLs), auto-expire after 90 days, deletable at any time
  (Settings → "Delete my investigations, briefings and files").
* Third-party processing: uploaded files and prompts are processed by the model providers routed through OpenRouter
  (OpenAI, Google). This is disclosed in Settings → Data & privacy. Production would require DPAs and EU data residency choices.
* Logs never contain API keys, JWTs, document contents or full transcripts; user ids are hashed in logs.
* Authentication by Amazon Cognito (passwords never touch our backend in AWS).

## Data licensing
* yfinance/Yahoo data: personal/research use — acceptable for an academic prototype, not for a commercial launch
  (would require a licensed market data feed).
* GDELT, SEC EDGAR, FRED: public data; SEC fair-access rules respected (User-Agent, low request rate).
* News: only headlines + links to original publishers; no article bodies are copied.
* Demo audio/PDF are synthetic and refer to a fictional company; no copyrighted media in the repository.

## AI safety controls
* Numbers are computed in Python; models interpret them.
* Pydantic validation of every model output (one correction retry, then graceful degradation).
* Unknown evidence ids removed; unsupported factual claims dropped; quotes verified verbatim against transcripts.
* "Not enough evidence available" is preferred to speculation (prompted and visible in the UI).
