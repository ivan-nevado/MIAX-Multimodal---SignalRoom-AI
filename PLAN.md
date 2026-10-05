You are acting as the lead software engineer, AI engineer, cloud architect, product designer, and technical founder for a FinTech startup MVP called **SignalRoom AI**.

Your task is to **build the complete functional MVP directly in the current repository**. Do not merely explain what should be built. Create the files, folders, code, Terraform, Dockerfiles, tests, documentation, seed/demo data, and frontend UI.

Do not ask me unnecessary clarification questions. Make sensible engineering decisions yourself and document assumptions. Only stop and ask if something is genuinely impossible without a missing credential or external configuration. In those cases, implement everything else with a clean placeholder and `.env.example`.

The application is an AI-native financial intelligence platform.

## 1. PRODUCT

### Startup

Name: **SignalRoom AI**

Tagline:

> **Know what moved the market. Know why.**

Positioning:

> SignalRoom is an AI financial intelligence room that combines market data, news, financial filings, charts, and audio into one coordinated research workflow.

The core idea is NOT “a chatbot that summarizes financial news”.

The core idea is:

> **A team of specialized AI agents investigates market events, cross-checks evidence across different modalities, and produces a concise explanation of what happened, why it likely happened, and what matters next.**

The product should feel like an AI research team rather than an LLM wrapper.

### Primary use case

The killer feature is:

> **“Why did this asset move?”**

Example:

User selects NVIDIA.

SignalRoom gathers:

* market price and historical movement
* volume
* relevant news
* financial information
* SEC information where applicable
* macro context
* optional uploaded documents
* optional uploaded audio
* optional uploaded screenshots/charts

The agent team investigates the event and generates:

* what happened
* likely drivers
* evidence supporting each driver
* sentiment shift
* risk assessment
* market context
* source links
* a short executive summary
* optional audio briefing

The system must distinguish clearly between:

* observed facts
* derived quantitative metrics
* model interpretation
* hypotheses / likely drivers

Never present model-generated causality as proven causality.

Use wording such as:

* “likely driver”
* “consistent with”
* “the evidence suggests”
* “possible contributing factor”

Do NOT say “X caused the stock to fall” unless a source explicitly establishes causality.

---

# 2. MVP SCOPE

Build these main flows.

### Flow A — Dashboard

After login the user sees:

* market overview
* watchlist
* recent major moves
* “Why?” buttons
* latest important financial events
* daily briefing
* audio briefing
* recent investigations

### Flow B — Asset investigation

User clicks:

> NVIDIA → Why?

The system creates an investigation.

The frontend immediately shows progress:

```text
Investigating NVIDIA

✓ Market data collected
✓ Relevant news identified
✓ News clustered
✓ Financial context analyzed
✓ Risk analysis completed
● Synthesizing evidence
○ Generating briefing
```

This is an asynchronous long-running job.

When complete, the result includes:

* asset movement
* key drivers
* evidence
* sentiment
* risk
* market context
* event timeline
* source list
* charts
* optional audio

### Flow C — Research workspace

User can create an investigation manually.

Inputs:

* company/ticker
* natural-language question
* optional PDF/document
* optional image/screenshot
* optional audio file

Examples:

> Why is Tesla down today?

> Compare today's move with the latest earnings report.

> Does this earnings report change the investment thesis?

> Analyze this chart.

> Summarize this earnings call and identify the most important risks.

### Flow D — Daily briefing

The user can enable:

> Daily Market Briefing

The user selects:

* enabled/disabled
* desired local time
* timezone
* watchlist

Every day SignalRoom automatically creates a personalized briefing.

The briefing contains:

* top market events
* major watchlist movements
* relevant news
* sentiment shifts
* macro events
* risk flags
* source links
* short written summary
* optional generated audio

### Flow E — Email

When daily briefing email is enabled:

* generate the briefing
* send an HTML email via Amazon SES
* include concise summaries
* include links back to SignalRoom
* include source links
* include a “Listen to briefing” link when audio exists

Do not send email automatically unless the user explicitly enables it.

---

# 3. PRODUCT PRINCIPLES

The product must feel:

* premium
* financial
* intelligent
* calm
* trustworthy
* analytical
* modern
* fast

It must NOT look like:

* a generic AI chat application
* a crypto trading dashboard
* a template SaaS dashboard
* an over-designed neon “AI startup”
* a gambling/trading app

This is an intelligence/research product.

The UI should prioritize:

> signal → context → evidence → details

---

# 4. BRAND / DESIGN SYSTEM

Use a cohesive dark financial interface.

### Colors

Define design tokens rather than hardcoding colors throughout the application.

Suggested palette:

```text
Background:          #08090D
Surface:             #101219
Surface elevated:    #171922
Border:              #262936

Primary violet:      #8B5CF6
Accent pink:         #EC4899

Text primary:        #F5F5F7
Text secondary:      #A1A1AA
Text muted:          #71717A

Positive:            #22C55E
Negative:            #EF4444
Warning:             #F59E0B
```

Use positive/negative colors sparingly.

Do not make the whole UI neon.

### Typography

Use:

* **Space Grotesk** for headings and high-level product typography
* **Inter** for body text, tables, UI controls, and dense financial information

Use a type scale consistently.

Headings should feel strong and editorial.

Financial numbers should use a visually clear numeric style.

### Icons

Use Lucide icons consistently.

Do not use random emoji as interface icons.

### Components

Use:

* React
* TypeScript
* Tailwind CSS
* shadcn/ui-style components
* Lucide
* Framer Motion for subtle transitions

Keep component design consistent.

---

# 5. FRONTEND STRUCTURE

Use React + TypeScript.

Prefer Vite.

Structure approximately as:

```text
frontend/
  src/
    app/
      router/
      providers/
    components/
      ui/
      layout/
      navigation/
      charts/
      investigations/
      evidence/
      briefing/
      agents/
      watchlist/
      files/
    features/
      auth/
      dashboard/
      assets/
      investigations/
      briefings/
      settings/
    hooks/
    lib/
      api/
      auth/
      formatting/
      charts/
    types/
    pages/
      LandingPage.tsx
      LoginPage.tsx
      SignupPage.tsx
      ForgotPasswordPage.tsx
      DashboardPage.tsx
      AssetPage.tsx
      ResearchPage.tsx
      InvestigationPage.tsx
      BriefingPage.tsx
      SettingsPage.tsx
    App.tsx
    main.tsx
  public/
```

Keep page components thin.

Business logic must not live inside React components.

---

# 6. FRONTEND ROUTING

Create:

```text
/
  landing page

/login
/signup
/forgot-password

/app
  protected application

/app/dashboard
/app/asset/:symbol
/app/research
/app/investigation/:id
/app/briefing/:id
/app/settings
```

Unauthenticated users trying to access `/app/*` must be redirected to login.

Authenticated users visiting `/` can be redirected to `/app/dashboard` or allowed to view the landing page depending on UX, but choose one consistent behavior.

---

# 7. LANDING PAGE

Build a real startup landing page.

Use SignalRoom branding.

### Hero

Headline:

> **Know what moved the market. Know why.**

Subheadline:

> SignalRoom combines market data, news, financial filings, charts and audio into one AI research workflow.

Primary CTA:

> Start researching

Secondary CTA:

> See how it works

### Section: The problem

Explain:

> Markets generate enormous amounts of information across different formats.

Show:

```text
News
Financial reports
Charts
Earnings calls
Market data
Macro events
```

then:

> SignalRoom turns them into one coherent intelligence layer.

### Section: AI research team

Visually show:

```text
Market Scout
News Scout
Financial Analyst
Risk Analyst
Research Analyst
Chief Editor
```

Each with one concise responsibility.

### Section: multimodal

Show:

```text
PDF
Image
Audio
Market data
News
Text
        ↓
SignalRoom
        ↓
Research Brief
```

### Section: Why?

Use a polished fake/seeded demonstration:

```text
NVIDIA
-6.2%

Why?

62%  Regulatory / export news
21%  Valuation concerns
17%  Market / sector pressure
```

Do not represent these percentages as real machine-learning probabilities.

Label them:

> Evidence-weighted contribution

### Section: Daily briefing

Show written briefing and audio player.

### Section: Sources / evidence

Show how every conclusion can expand to the evidence behind it.

### Pricing section

This is a startup concept, not a payment implementation.

Use conceptual plans:

**Free**

* basic watchlist
* daily market brief
* limited investigations

**Pro**

* deeper investigations
* multimodal uploads
* personalized audio briefings
* larger watchlists

Do not implement Stripe unless it is trivial and clearly separated from the MVP.

### Footer

Include:

* Product
* Research
* About
* Privacy
* Terms
* Educational disclaimer

Add:

> SignalRoom is an educational research prototype and does not provide personalized investment advice or execute trades.

---

# 8. LOGIN / AUTHENTICATION

Use **Amazon Cognito User Pools**.

Authentication method:

* email + password
* email verification
* forgot password
* logout
* session persistence

Do not implement social login unless it can be added without significantly increasing complexity.

Frontend should receive Cognito tokens.

Backend must validate JWTs properly using Cognito's JWKS.

Do not trust a user ID sent from the browser.

The backend must derive the authenticated user ID from the validated JWT.

Structure:

```text
frontend
  ↓
Cognito
  ↓
JWT
  ↓
FastAPI
  ↓
JWT validation
  ↓
user_id
```

Use a public Cognito SPA app client without a client secret.

Create a protected route system.

---

# 9. FRONTEND ↔ BACKEND COMMUNICATION

Use REST APIs for standard operations.

Use asynchronous jobs for long-running AI investigations.

Recommended structure:

```text
React
  ↓
HTTPS
  ↓
FastAPI
  ↓
SQS
  ↓
ECS Worker
  ↓
LangGraph
  ↓
AI agents
```

For normal reads/writes:

```text
React
  ↓
fetch / React Query
  ↓
FastAPI
```

Use React Query/TanStack Query for:

* caching
* loading state
* retries
* invalidation

Do not put API keys in the frontend.

---

# 10. REAL-TIME INVESTIGATION PROGRESS

Do not keep the HTTP request open while an investigation is executing.

Instead:

```text
POST /api/v1/investigations
```

returns immediately:

```json
{
  "investigation_id": "...",
  "status": "queued"
}
```

Then the worker runs independently.

Implement progress updates.

Preferred approach:

```text
GET /api/v1/investigations/{id}/events
```

as Server-Sent Events.

The worker writes progress events to DynamoDB.

Frontend receives:

```text
queued
running
market_data
news
financial
risk
synthesis
audio
completed
failed
```

If SSE fails, the frontend should fall back to periodic polling.

Do not use WebSockets unless there is a clear technical reason.

---

# 11. ASYNC VS BACKGROUNDTASKS VS CRON

This distinction is important.

### FastAPI async endpoints

Use `async def` for:

* API requests
* database/network I/O
* S3 presigned URL creation
* reading DynamoDB
* provider requests when async clients exist

### FastAPI BackgroundTasks

Use BackgroundTasks ONLY for tiny non-critical tasks.

Examples:

* fire-and-forget analytics
* lightweight audit logging
* very small post-response housekeeping

Do NOT use FastAPI BackgroundTasks for:

* agent execution
* PDF analysis
* audio transcription
* TTS generation
* daily briefings
* large external API workflows

Those tasks can be lost if the container restarts.

### SQS worker

Use SQS + ECS Worker for:

* investigations
* document processing
* image analysis
* audio transcription
* daily briefing generation
* TTS
* email generation
* heavy agent workflows

### Scheduled jobs

Use **Amazon EventBridge Scheduler**.

Do not create a cron process inside the FastAPI container.

Use EventBridge Scheduler to periodically start the worker job.

For the MVP, use a central schedule, for example every 15 minutes.

The worker checks which users are due for a daily briefing based on:

* enabled
* user's timezone
* preferred local time
* last sent date

Use idempotency so the same user cannot receive the same daily briefing twice.

This avoids creating a separate EventBridge schedule for every user.

Example conceptual flow:

```text
EventBridge Scheduler
        ↓
Daily Scheduler ECS Task
        ↓
Find users due
        ↓
Create briefing jobs
        ↓
SQS
        ↓
Worker
        ↓
Agents
        ↓
Store briefing
        ↓
Generate TTS
        ↓
SES
```

---

# 12. AWS ARCHITECTURE

Use AWS and Terraform.

The architecture should be:

```text
                           INTERNET
                              |
                         CloudFront
                       /             \
                      /               \
               S3 Frontend          ALB
                                        |
                                   ECS Fargate
                                   FastAPI API
                                        |
                         -----------------------------
                         |             |             |
                      DynamoDB        S3           SQS
                                                       |
                                                 ECS Worker
                                                       |
                                      --------------------------------
                                      |              |               |
                                    OpenAI         Gemini          Data APIs
```

Authentication:

```text
React
  ↓
Cognito
  ↓
JWT
  ↓
FastAPI
```

Email:

```text
Worker
  ↓
Amazon SES
```

Scheduled:

```text
EventBridge Scheduler
  ↓
ECS scheduled worker
```

---

# 13. TERRAFORM STRUCTURE

Create:

```text
terraform/
  modules/
    networking/
    ecr/
    ecs/
    alb/
    s3/
    cloudfront/
    cognito/
    dynamodb/
    sqs/
    eventbridge/
    secrets-manager/
    iam/
    ses/

  environments/
    dev/
      main.tf
      variables.tf
      outputs.tf
      provider.tf
      versions.tf
      terraform.tfvars.example
```

Each module must be independently understandable.

Do not put all infrastructure into one giant `main.tf`.

Use outputs between modules.

Add comments where an AWS configuration is non-obvious.

Do not hardcode:

* AWS account IDs
* region
* domain
* passwords
* API keys
* secrets

Use variables.

Default AWS region:

```text
eu-west-1
```

but make it configurable.

---

# 14. AWS COST CONSTRAINT

This is an academic MVP.

Avoid unnecessarily expensive infrastructure.

Do NOT introduce:

* NAT Gateway unless absolutely necessary
* Kubernetes/EKS
* OpenSearch
* Redshift
* MSK/Kafka
* ElastiCache/Redis
* RDS unless there is a concrete need
* paid vector database
* paid news data provider

Use:

* ECS Fargate
* DynamoDB
* S3
* SQS
* EventBridge Scheduler
* Cognito
* CloudFront
* ALB
* SES
* Secrets Manager
* CloudWatch

For the MVP, public-subnet ECS Fargate with appropriately restricted security groups is acceptable if it significantly reduces unnecessary networking cost. Document that production would move workloads to private subnets with appropriate egress controls.

---

# 15. SECRETS

Secrets MUST be managed through **AWS Secrets Manager** in the deployed application.

Never:

* hardcode keys
* commit keys
* put real API keys into Terraform source
* put real API keys into GitHub Actions
* expose secrets to React

Create a Secrets Manager secret for application keys.

Use ECS task definition secret references or another secure runtime retrieval mechanism.

The source of truth in AWS is Secrets Manager.

Suggested secrets:

```text
OPENAI_API_KEY
GEMINI_API_KEY
ALPHAVANTAGE_API_KEY
FRED_API_KEY
SEC_USER_AGENT
SES_FROM_EMAIL
```

Not every integration must be enabled.

`ALPHAVANTAGE_API_KEY` and `FRED_API_KEY` can be optional.

Terraform should create the secret container, but do NOT put actual credentials into Terraform code/state.

Provide a script such as:

```text
scripts/set_secrets.sh
```

which uses AWS CLI to populate the Secrets Manager value.

For local development:

```text
.env
```

may be used, but:

```text
.env
.env.local
```

must be in `.gitignore`.

Create:

```text
.env.example
```

with names only.

---

# 16. STORAGE

Use S3 for user-uploaded files and generated media.

Structure:

```text
signalroom-bucket/
  users/
    {user_id}/
      investigations/
        {investigation_id}/
          input/
            documents/
            images/
            audio/
          output/
            reports/
            audio/
```

Never make this bucket public.

Use presigned URLs for browser uploads/downloads.

The browser should upload large files directly to S3.

Flow:

```text
React
  ↓
POST /uploads/presign
  ↓
FastAPI
  ↓
presigned S3 URL
  ↓
React directly uploads
  ↓
S3
  ↓
POST /uploads/complete
  ↓
backend queues processing
```

Do not send large PDFs/audio through FastAPI.

Validate:

* MIME type
* file size
* extension
* ownership/path

---

# 17. DATABASE

Use DynamoDB.

Do not introduce a relational database unless it is clearly necessary.

Create tables for:

### users

Stores:

* user ID
* email
* preferences
* timezone
* briefing preferences
* created_at

### watchlists

Stores:

* user_id
* asset symbol
* display name
* asset type
* added_at

### investigations

Stores:

* investigation_id
* user_id
* asset
* question
* status
* created_at
* completed_at
* final_result
* input references
* summary
* impact drivers
* evidence

### investigation_events

Stores:

* investigation_id
* timestamp
* event type
* message
* metadata

Add TTL for old transient event data if appropriate.

### briefing_deliveries

Use this for idempotency:

```text
user_id + date + briefing_type
```

so a daily briefing is never sent twice.

---

# 18. DATA SOURCES

Very important:

**The product must use free or free-for-educational-project data sources. Do not make the MVP depend on paid proprietary financial datasets.**

Use provider abstraction interfaces.

Suggested provider stack:

## Market data: yfinance

Use the Python `yfinance` package as the initial no-key market data adapter.

Use it for:

* historical OHLCV
* current/previous price data where available
* volume
* returns
* basic ticker metadata
* ETF/index/crypto symbols supported by Yahoo Finance

The application must never assume the data is exchange-grade real-time data.

Display:

> Market data may be delayed. Educational prototype.

Cache results aggressively to avoid unnecessary requests.

Make the provider replaceable.

Create:

```text
backend/app/integrations/market/yahoo.py
```

and an interface:

```text
MarketDataProvider
```

Do not let the agents import `yfinance` directly.

Important:

yfinance is an unofficial open-source interface to Yahoo Finance and is intended by its documentation for personal/research use, so treat it as an academic prototype data source rather than a production licensed market-data feed.

## SEC

Use the official public SEC EDGAR APIs for U.S. company financial data.

No API key is required.

Use HTTPX.

Include a descriptive SEC `User-Agent`.

Use SEC data for:

* company facts
* filings
* financial statement concepts
* filing metadata

Useful concepts include:

* revenue
* operating income
* net income
* assets
* liabilities
* cash
* debt
* shares

Do not scrape the SEC website unnecessarily.

Create:

```text
backend/app/integrations/financial/sec.py
```

with caching and polite request behavior.

## News: GDELT

Use GDELT DOC 2.0 as the no-key global news source.

Use it for:

* article discovery
* news volume
* tone/sentiment timeline
* source metadata
* event discovery

Do not hammer the API.

Use:

* low request volume
* caching
* retries with exponential backoff
* deduplication

Do not depend on scraping full publisher article bodies.

Store:

* title
* URL
* source domain
* publication/seen time
* GDELT metadata
* query used

When an article page itself is accessible and useful, fetching should be isolated and optional.

Always link to the original source rather than copying article content.

## Alpha Vantage — optional enhancement

Implement an optional Alpha Vantage provider for:

* structured market data
* news/sentiment

This is acceptable because Alpha Vantage provides a free service and explicitly supports verified open-source/educational projects.

However:

* do not make the entire application fail if the Alpha Vantage key is missing
* use GDELT/yfinance/SEC as fallback sources
* implement provider interfaces
* clearly document free-tier limitations and verification requirements

Do not depend on premium-only Alpha Vantage endpoints.

Do NOT make earnings-call transcripts a mandatory Alpha Vantage dependency.

## FRED — optional macro source

Use FRED for macroeconomic data if `FRED_API_KEY` is configured.

FRED requires an API key, but the account/key is free.

Use a small curated set of series, for example:

* Fed Funds Rate
* CPI
* unemployment
* GDP

Do not call FRED on every request.

Cache macro data.

Make macro analysis optional.

---

# 19. DATA PROVIDER ARCHITECTURE

Create:

```text
backend/app/integrations/
  market/
    base.py
    yahoo.py
    alpha_vantage.py

  news/
    base.py
    gdelt.py
    alpha_vantage.py

  financial/
    base.py
    sec.py

  macro/
    base.py
    fred.py

  storage/
    s3.py

  email/
    ses.py

  ai/
    openai.py
    gemini.py
```

Agents depend on interfaces.

Agents must NOT directly import:

```python
yfinance
httpx
boto3
openai
google.genai
```

The integration layer owns those details.

---

# 20. AI MODEL STRATEGY

Use a multi-model architecture.

## Main reasoning model

Use:

> **GPT-6 Luna**

Make the model name configurable:

```text
OPENAI_MODEL=gpt-6-luna
```

Use GPT-6 Luna primarily for:

* orchestration reasoning
* financial interpretation
* research synthesis
* risk reasoning
* report generation
* conversational follow-up

Do not hardcode the model ID in business logic.

Use an abstraction:

```text
LLMProvider
```

and:

```text
OpenAIProvider
```

## Multimodal document/image analysis

Use:

> **Gemini 3.8 Flash**

for multimodal:

* image understanding
* screenshots
* document page images
* charts contained in documents
* visual financial material

Make configurable:

```text
GEMINI_MULTIMODAL_MODEL=gemini-3.8-flash
```

Use structured outputs where possible.

## Audio to text

Use:

> `gemini-3.5-transcribe`

for uploaded audio.

It should support:

* language detection
* speaker diarization when useful
* transcription
* structured transcript output

Make configurable:

```text
GEMINI_TRANSCRIBE_MODEL=gemini-3.5-transcribe
```

## Text to speech

Use:

> `gemini-3.8-flash-tts`

for generated daily briefings.

Make configurable:

```text
GEMINI_TTS_MODEL=gemini-3.8-flash-tts
```

Use a consistent professional voice.

For a daily financial briefing, the voice should sound:

* calm
* confident
* analytical
* not sensationalist

The current TTS model supports long-form expressive narration.

## Image/video generation

Do NOT add image or video generation to the MVP.

The product does not need a generative image/video model.

Use actual frontend charts and diagrams for visual output instead.

If desired, document image/video generation as a future feature rather than implementing it.

---

# 21. AGENT ARCHITECTURE

Use **LangGraph** for agent orchestration.

Do not make one huge agent.

Create specialized agents.

Recommended:

```text
Orchestrator Agent
Market Agent
News Agent
Financial Agent
Sentiment Agent
Event Detection Agent
Risk Agent
Research / Evidence Agent
Synthesis Agent
Briefing Agent
Voice Agent
```

---

# 22. ORCHESTRATOR AGENT

The orchestrator receives:

```text
asset
user_question
available_inputs
```

It decides which agents are required.

Example:

```text
Question:
Why did NVIDIA fall today?

Run:
Market
News
Event Detection
Financial
Sentiment
Risk
Synthesis
```

Another question:

```text
Analyze this earnings call.
```

Run:

```text
Audio
Financial
Sentiment
Risk
Synthesis
```

Another:

```text
Analyze this screenshot.
```

Run:

```text
Vision
Market
Synthesis
```

Do not always run every agent.

The orchestrator should minimize unnecessary calls.

---

# 23. MARKET AGENT

Responsibilities:

* current movement
* historical movement
* volume
* volatility
* drawdown
* relative movement where data allows
* abnormal moves
* technical context

Tools:

```text
get_quote
get_history
calculate_returns
calculate_volatility
calculate_drawdown
calculate_volume_change
detect_unusual_move
```

Important:

The actual numerical calculations must be performed in Python.

Do not ask the LLM to calculate financial statistics from raw arrays.

Return structured output:

```json
{
  "symbol": "NVDA",
  "move_pct": -6.2,
  "volume_change_pct": 184,
  "volatility_20d": 0.31,
  "drawdown_30d": -8.4,
  "anomaly_score": 0.92
}
```

The LLM interprets the metrics, it does not replace deterministic computation.

---

# 24. NEWS AGENT

Responsibilities:

* search relevant news
* deduplicate stories
* cluster related articles
* identify major themes
* score relevance

Tools:

```text
search_news
get_news_timeline
get_news_tone
cluster_articles
```

Do not send dozens of raw articles to GPT.

Pipeline:

```text
query
↓
retrieve
↓
deduplicate
↓
rank
↓
cluster
↓
summarize clusters
```

Return:

```json
{
  "clusters": [
    {
      "cluster_id": "...",
      "theme": "Export restrictions",
      "articles": [],
      "relevance": 0.94
    }
  ]
}
```

---

# 25. SENTIMENT AGENT

Responsibilities:

* article sentiment
* topic sentiment
* sentiment changes
* agreement/disagreement between sources

Do not call an LLM “confidence” a factual probability.

Use a field called:

```text
evidence_confidence
```

which reflects source coverage and agreement.

Example:

```text
Evidence confidence: High

Reason:
7 independent relevant sources discuss the same event.
```

Avoid fake statistical precision.

Visualize:

```text
Sentiment
  |
+1|      ███
  |
  |  ██
  |
  |                  █
  |
-1|-----------------------------
      -7d         today
```

---

# 26. FINANCIAL AGENT

Responsibilities:

* financial statements
* SEC facts
* revenue
* margins
* earnings
* debt
* cash
* guidance
* year-over-year change
* quarter-over-quarter change

Use deterministic Python calculations.

Return:

```json
{
  "revenue_growth": 0.18,
  "operating_margin": 0.32,
  "net_margin": 0.28,
  "cash": 12300000000,
  "debt": 4500000000
}
```

The LLM should explain the information.

Never fabricate missing financial values.

Use:

```text
null
```

when data is unavailable.

---

# 27. DOCUMENT AGENT

When a user uploads a PDF:

Pipeline:

```text
S3
 ↓
document ingestion
 ↓
PDF parser
 ↓
text extraction
 ↓
page rendering
 ↓
Gemini multimodal analysis where needed
 ↓
structured document facts
```

Use text extraction first.

Use vision for:

* financial tables
* charts
* graphs
* layouts where text extraction loses structure

Do not send an entire 200-page annual report blindly to an LLM.

First:

* detect page count
* extract text
* identify relevant pages
* analyze only relevant sections/pages

Store extracted results.

---

# 28. IMAGE / SCREENSHOT AGENT

User uploads:

* chart screenshot
* financial graph
* investor presentation page
* document image

Use Gemini 3.8 Flash.

Pipeline:

```text
S3
 ↓
image preprocessing
 ↓
Gemini vision
 ↓
structured interpretation
 ↓
Market/Financial agents
 ↓
Synthesis
```

The model should return:

```json
{
  "image_type": "price_chart",
  "observations": [],
  "uncertainties": [],
  "relevant_levels": [],
  "interpretation": ""
}
```

Never pretend that visual technical analysis is certain.

---

# 29. AUDIO AGENT

User uploads:

* earnings call
* analyst call
* meeting
* financial briefing

Pipeline:

```text
S3
 ↓
Gemini 3.5 Transcribe
 ↓
transcript
 ↓
speaker segmentation
 ↓
Earnings Agent
 ↓
Financial Agent
 ↓
Sentiment Agent
 ↓
Risk Agent
 ↓
Synthesis
```

Store transcript metadata, not unnecessary copies.

Do not automatically download copyrighted earnings-call audio from random websites.

For demo data, create a synthetic short earnings-call script and optionally generate its audio using Gemini TTS.

This makes the demo reproducible without depending on copyrighted third-party media.

---

# 30. EVENT DETECTION AGENT

This agent turns raw information into events.

Potential event types:

```text
earnings
guidance_change
regulation
lawsuit
management_change
m_and_a
product
analyst_action
macro
sector_move
other
```

Build an event timeline:

```text
09:02
News event

09:18
Large volume spike

10:04
Additional regulatory report

11:25
Management statement

14:42
Price reaches daily low
```

Events should contain source references whenever possible.

---

# 31. RISK AGENT

Analyze:

* regulatory risk
* valuation risk
* operational risk
* competition
* macro risk
* liquidity
* concentration
* governance where supported by evidence

Use qualitative levels:

```text
LOW
MEDIUM
HIGH
```

Do not output fake probabilities unless calculated from a documented statistical model.

Example:

```json
{
  "risk": "regulatory",
  "level": "HIGH",
  "reason": "...",
  "evidence_ids": ["source-1", "source-4"]
}
```

---

# 32. RESEARCH / EVIDENCE AGENT

This agent is critical.

Its responsibility is to ensure that important claims have supporting evidence.

For each claim create:

```text
claim_id
claim
claim_type
evidence_ids
source_count
evidence_confidence
```

Example:

```json
{
  "claim_id": "c1",
  "claim": "Export restrictions are the main reported concern.",
  "claim_type": "interpretation",
  "evidence_ids": ["n1", "n3", "n7"],
  "source_count": 3,
  "evidence_confidence": "high"
}
```

The final synthesis cannot create unsupported factual claims.

---

# 33. SYNTHESIS AGENT

This is the “investment committee” equivalent.

It receives outputs from all specialist agents.

Responsibilities:

* reconcile disagreements
* prioritize evidence
* distinguish fact vs interpretation
* produce final explanation

Output:

```text
Executive Summary
What Happened
Likely Drivers
Market Context
Financial Context
Sentiment
Risks
What To Watch
Evidence
```

The model should explicitly identify uncertainty.

Do not generate “buy/sell” recommendations.

The product is an intelligence/research system, not an execution or personalized advisory platform.

---

# 34. “WHY?” ANALYSIS

This must be the main product interaction.

Example UI:

```text
NVIDIA
$XXX
-6.2%

WHY?

Primary driver
Export restrictions

Evidence-weighted contribution
62%

Secondary
Valuation concerns
21%

Market pressure
17%
```

Important:

These percentages are NOT probabilities.

They are a transparent heuristic contribution score based on things such as:

* source relevance
* number of supporting sources
* event timing
* market move timing
* tone shift
* source agreement

Implement this score deterministically in Python.

Document the formula.

Do not let an LLM invent these numbers.

---

# 35. EVIDENCE GRAPH

Implement a visual evidence graph.

Use **React Flow**.

Example:

```text
                    NVIDIA -6.2%
                           |
               +-----------+-----------+
               |                       |
        Export restrictions      Valuation concerns
               |                       |
        +------+------+               |
        |      |      |               |
      Source Source Source          Source
        1      2      3               4
```

Clicking a source opens:

* publisher
* title
* date
* source link

This is one of the most important visual differentiators of the product.

---

# 36. FRONTEND CHARTS

Do not generate charts with an image model.

Charts should be generated from structured numeric data.

Use:

### Lightweight Charts

For:

* candlestick charts
* OHLC
* volume

### Recharts

For:

* sentiment
* news volume
* risk
* macro
* comparisons
* time series

Create reusable chart components:

```text
PriceChart
CandlestickChart
VolumeChart
SentimentTimeline
NewsVolumeChart
RiskRadar
MarketComparisonChart
MacroSparkline
```

Charts must have:

* responsive sizing
* tooltips
* date formatting
* loading state
* empty state
* error state

Avoid clutter.

---

# 37. OTHER UI VISUALIZATIONS

Implement as many useful visual outputs as practical:

### Agent execution timeline

```text
Market ✓
News ✓
Financial ✓
Risk ✓
Synthesis ✓
```

### Event timeline

### Sentiment timeline

### Market movement chart

### Volume spike chart

### Evidence graph

### Risk matrix

```text
            IMPACT
HIGH        🔴
MEDIUM      🟠
LOW         🟢
```

### Driver contribution

Horizontal bars.

### Financial KPI cards

Examples:

```text
Revenue growth
Operating margin
Debt
Cash
```

### Source cards

With:

* publisher
* timestamp
* relevance
* evidence tags

---

# 38. PROGRESSIVE DISCLOSURE

This is important for UX.

Do not show 50 pieces of information immediately.

Default:

```text
What happened?
Why?
What matters?
```

Then users can expand:

```text
Evidence
Market context
Financial context
Risk
Agent analysis
Raw sources
```

A user should be able to understand the key insight in under 30 seconds.

Experts should be able to drill down into the evidence.

---

# 39. DAILY BRIEFING

Create a generated daily briefing model:

```json
{
  "date": "...",
  "headline": "...",
  "top_events": [],
  "watchlist_moves": [],
  "macro_events": [],
  "risk_flags": [],
  "summary": "...",
  "audio_s3_key": null
}
```

The briefing agent should produce an editorial-style briefing.

Example:

```text
Good morning.

Three things matter today.

1. NVIDIA
Shares fell sharply after...
Why it matters: ...

2. ECB
Markets are focused on...
Why it matters: ...

3. Tesla
Shares rose...
```

The result should be readable both:

* in the web application
* as an email
* as audio

---

# 40. AUDIO BRIEFING

Pipeline:

```text
Daily briefing text
        ↓
Voice Agent
        ↓
Gemini 3.8 Flash TTS
        ↓
MP3/WAV
        ↓
S3
        ↓
presigned URL
        ↓
frontend audio player
```

Use a professional single voice.

Do not add background music.

Generate audio asynchronously.

The frontend must show:

```text
Preparing briefing audio...
```

then:

```text
▶ 4:12
```

---

# 41. EMAIL IMPLEMENTATION

Use Amazon SES.

Create:

```text
backend/app/integrations/email/ses.py
backend/app/templates/email/daily_briefing.html
```

Email template should match SignalRoom's UI.

Include:

* SignalRoom logo/name
* headline
* top 3 events
* watchlist movements
* risk flag
* CTA to open full briefing
* source links
* unsubscribe/preferences link

Do not put a huge amount of text in the email.

SES sandbox restrictions must be documented.

During development, assume the sender and recipient may need verification.

Create:

```text
docs/email_setup.md
```

with exact steps.

---

# 42. API STRUCTURE

Inside backend:

```text
backend/
  app/
    api/
      routes/
        auth.py
        users.py
        watchlists.py
        assets.py
        investigations.py
        uploads.py
        briefings.py
        preferences.py
        health.py
      dependencies.py
      router.py
```

The user explicitly wants an `api/` folder.

Do not mix routes with business logic.

---

# 43. BACKEND STRUCTURE

Use:

```text
backend/
  app/
    api/
    agents/
    workflows/
    integrations/
    services/
    repositories/
    models/
    schemas/
    config/
    utils/
    workers/
    prompts/
    skills/
    main.py

  tests/
```

### Suggested separation

`api/`

HTTP endpoints only.

`services/`

Business logic.

`repositories/`

DynamoDB/S3 persistence.

`integrations/`

External APIs and AI providers.

`agents/`

AI reasoning units.

`workflows/`

LangGraph workflows.

`schemas/`

Pydantic request/response models.

`workers/`

SQS and scheduled job execution.

`prompts/`

Agent prompts.

`skills/`

Reusable domain-specific skills.

---

# 44. AGENT SKILLS

Use skills only where useful.

Create:

```text
backend/app/skills/
  financial_analysis/
    SKILL.md
    references/
  market_analysis/
    SKILL.md
    references/
  news_research/
    SKILL.md
    references/
  risk_analysis/
    SKILL.md
    references/
  earnings_analysis/
    SKILL.md
    references/
  briefing_writing/
    SKILL.md
```

Follow progressive disclosure.

The agent should first load only the concise `SKILL.md`.

Detailed methodology lives in `references/`.

Do NOT put gigantic methodology documents into every agent prompt.

Example:

```text
SKILL.md
- purpose
- when to use
- inputs
- outputs
- rules
- important limitations

references/
  valuation.md
  accounting.md
  risk-framework.md
```

Skills should define behavior and constraints.

---

# 45. PROMPTS

Store prompts outside code where practical.

Example:

```text
backend/app/prompts/
  orchestrator.txt
  market_agent.txt
  news_agent.txt
  financial_agent.txt
  sentiment_agent.txt
  event_agent.txt
  risk_agent.txt
  evidence_agent.txt
  synthesis_agent.txt
  briefing_agent.txt
```

Do not build giant f-string prompts throughout Python files.

---

# 46. STRUCTURED AI OUTPUT

Use Pydantic models for agent outputs.

For example:

```python
class Driver(BaseModel):
    name: str
    explanation: str
    contribution_score: float
    evidence_ids: list[str]
```

```python
class InvestigationResult(BaseModel):
    summary: str
    what_happened: str
    drivers: list[Driver]
    risks: list[Risk]
    claims: list[Claim]
    sources: list[Source]
```

Validate every model response.

If parsing fails:

1. retry once with a correction prompt
2. log the failure
3. mark investigation as failed gracefully

Never silently accept malformed JSON.

---

# 47. INVESTIGATION STATE MACHINE

Use clear states:

```text
queued
running
collecting_data
analyzing
synthesizing
generating_audio
completed
failed
```

Every transition should be persisted.

The frontend must always know:

* current state
* percentage
* current agent
* human-readable status message

Do not fake progress.

Progress events should correspond to actual completed steps.

---

# 48. SQS

Use SQS for long-running work.

Create:

```text
investigation-queue
investigation-dlq
briefing-queue
briefing-dlq
```

Add:

* visibility timeout
* retry policy
* dead-letter queue
* idempotent job IDs

Worker must be able to retry safely.

An investigation should not produce duplicate audio or duplicate emails if the worker is restarted.

---

# 49. WORKER

Use a dedicated ECS Fargate worker service.

It can run:

```text
python -m app.workers.sqs_worker
```

The worker:

1. polls SQS
2. receives a job
3. validates payload
4. starts LangGraph
5. updates DynamoDB progress
6. saves output
7. acknowledges the message only after success

If the worker crashes before acknowledgment, SQS should make the message available again.

Implement proper exception handling.

---

# 50. SCHEDULED BRIEFING WORKER

Have a separate command:

```text
python -m app.workers.daily_briefing_scheduler
```

It should:

1. determine current UTC time
2. identify users whose local briefing window matches
3. create idempotency key
4. create briefing job
5. send to SQS
6. exit

This should be a one-shot ECS task invoked by EventBridge Scheduler.

Do not run an endless cron loop inside the application.

---

# 51. CACHE

Use caching heavily.

Examples:

* market history: minutes/hours
* daily fundamentals: hours/day
* news queries: minutes
* macro data: hours/day
* SEC facts: hours/day

Cache keys must include:

```text
provider
asset
query
time window
```

Use DynamoDB TTL where appropriate.

Do not call the same external source repeatedly during one investigation.

---

# 52. DATA FRESHNESS

Every external datum should record:

```text
source
retrieved_at
published_at if available
```

Frontend should display:

> Updated 8 minutes ago

or:

> Published 1 hour ago

Do not imply data is real-time unless it actually is.

---

# 53. ENTITY RESOLUTION

Users may enter:

```text
NVIDIA
Nvidia
NVDA
Tesla
Bitcoin
S&P 500
```

Build a simple resolver:

```text
NVIDIA -> NVDA
Tesla -> TSLA
Bitcoin -> BTC-USD
S&P 500 -> ^GSPC
EUR/USD -> EURUSD=X
```

Allow users to select from search results.

Do not rely entirely on the LLM for ticker resolution.

---

# 54. USER WATCHLIST

Allow:

* add asset
* remove asset
* reorder
* maximum MVP watchlist size
* asset search

Persist it in DynamoDB.

Seed demo watchlist:

```text
NVDA
TSLA
BTC-USD
^GSPC
EURUSD=X
```

Use these for the initial demo.

---

# 55. DEMO MODE

The professor must be able to run the project easily.

Create a demo mode.

Potential:

```text
VITE_DEMO_MODE=true
```

In demo mode:

* show seeded watchlist
* use static demo investigation data when external APIs are unavailable
* allow navigating the complete UI
* allow seeing evidence graph
* allow seeing charts
* allow seeing agent progress
* do not require API credentials just to explore the UI

However, the real implementation must remain available.

Create:

```text
demo_data/
  assets.json
  investigation.json
  news.json
  financials.json
  briefing.json
  earnings_call.txt
```

Also create a script:

```text
scripts/generate_demo_audio.py
```

which can use Gemini TTS to create a synthetic short earnings-call audio file.

Do not use copyrighted audio in the repository.

---

# 56. API ENDPOINTS

Implement at minimum:

```text
GET    /api/v1/health

GET    /api/v1/me
PATCH  /api/v1/me/preferences

GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{symbol}

GET    /api/v1/assets/search?q=
GET    /api/v1/assets/{symbol}

POST   /api/v1/investigations
GET    /api/v1/investigations/{id}
GET    /api/v1/investigations/{id}/events
DELETE /api/v1/investigations/{id}

POST   /api/v1/uploads/presign
POST   /api/v1/uploads/complete

GET    /api/v1/briefings
GET    /api/v1/briefings/{id}
POST   /api/v1/briefings/generate

GET    /api/v1/preferences/briefing
PATCH  /api/v1/preferences/briefing
```

Use versioned APIs.

---

# 57. SECURITY

Implement:

* JWT authentication
* authorization by user ID
* CORS configuration
* security headers where appropriate
* rate limiting at API level if reasonable
* input validation
* upload size validation
* MIME validation
* S3 private buckets
* presigned URLs
* structured logging without secrets
* no API keys in client
* no sensitive data in logs

A user must never be able to:

* retrieve another user's investigation
* retrieve another user's S3 file
* modify another user's watchlist
* modify another user's preferences

---

# 58. OBSERVABILITY

Add:

* structured JSON logs
* request ID
* investigation ID
* job ID
* user ID hash/reference where appropriate
* agent name
* provider name
* elapsed time
* error type

Do not log:

* API keys
* JWTs
* uploaded document contents
* full transcripts
* secrets

Use CloudWatch Logs.

Include health checks for:

* API
* DynamoDB connectivity
* S3
* provider configuration

Do not make health check fail simply because an optional external API key is missing.

---

# 59. ERROR UX

Every async operation must have graceful states.

Example:

```text
Could not complete the investigation.

Market data was available, but the news provider was unavailable.

You can retry.
```

Do not display:

```text
Traceback...
```

to users.

Backend logs the detailed error.

Frontend gets safe user-facing errors.

---

# 60. EMPTY STATES

Build good empty states.

Examples:

No watchlist:

> Build your market
> Add companies, indices and assets you want to monitor.

No briefing:

> Your first briefing will appear here.

No investigations:

> Ask SignalRoom what is happening in your market.

No source:

> No supporting source was found.

Do not invent evidence.

---

# 61. ACCESSIBILITY

Implement:

* keyboard navigation
* focus states
* semantic buttons
* labels
* aria attributes where necessary
* sufficient contrast
* responsive layout

Do not rely solely on color to communicate positive/negative.

---

# 62. RESPONSIVE DESIGN

Desktop should be the primary experience.

Also support:

* tablet
* mobile

On mobile:

* sidebar becomes drawer
* charts become horizontally scrollable where necessary
* evidence graph becomes stacked or simplified
* cards remain readable

---

# 63. MOBILE NAVIGATION

Use:

```text
Home
Research
Watchlist
Briefing
Settings
```

Desktop can use a sidebar.

---

# 64. ASSET PAGE

For `/app/asset/:symbol` show:

```text
NVIDIA
NVDA

$XXX
-6.2%

[1D] [1W] [1M] [1Y]

Price chart
Volume chart

WHY?
Main drivers

Latest news

Financial snapshot

Risk radar

Recent events
```

Primary CTA:

> Investigate why

---

# 65. INVESTIGATION PAGE

Top section:

```text
NVIDIA
Why did the stock move today?
```

Then:

```text
[Summary]
[Drivers]
[Evidence]
[Market]
[Financials]
[Risk]
[Sources]
```

Right side on desktop:

```text
Investigation status
Agent timeline
```

When completed:

```text
Listen to briefing ▶
```

---

# 66. CHAT / FOLLOW-UP

Provide a lightweight follow-up question field on the investigation page.

Example:

> What would invalidate this explanation?

or:

> Compare today's move with the last earnings report.

This should use the existing investigation context rather than starting from scratch.

Do not build a generic open-ended chatbot as the main interface.

The research object is the investigation.

---

# 67. INVESTIGATION CONTEXT

Persist:

* original question
* asset
* source references
* agent findings
* uploaded files
* final synthesis

Follow-up questions should use that structured context.

Do not re-run all agents unless needed.

The orchestrator should determine the minimal new work required.

---

# 68. SOURCE HANDLING

Every source object:

```json
{
  "id": "source_123",
  "title": "...",
  "publisher": "...",
  "url": "...",
  "published_at": "...",
  "retrieved_at": "...",
  "source_type": "news",
  "relevance": 0.91
}
```

Never fabricate source URLs.

Never invent publishers.

Always distinguish:

* source timestamp
* retrieval timestamp

---

# 69. FINANCIAL CALCULATIONS

Implement reusable Python functions for:

```text
percentage_change
log_return
rolling_volatility
maximum_drawdown
volume_change
z_score
moving_average
relative_performance
sentiment_change
news_volume_change
```

Add unit tests.

Use numpy/pandas when appropriate.

The LLM only interprets the structured metrics.

---

# 70. NEWS IMPACT SCORING

Implement a transparent deterministic heuristic.

For example:

```text
impact_score =
  relevance
  × source_support
  × temporal_alignment
  × sentiment_shift
```

Normalize to 0-100 or 0-1.

Document exactly how it is computed.

Do not pretend this is a statistically estimated causal model.

Call it:

> Evidence-weighted driver score.

---

# 71. INVESTMENT / FINANCIAL DISCLAIMER

The application should visibly state:

> SignalRoom is an educational financial research prototype. Its analysis is generated from available data and AI models and may contain errors. It does not provide personalized investment advice, execute trades, or guarantee the accuracy or completeness of market information.

Put a lighter version in the dashboard footer.

Put a full version in the Settings/About section.

---

# 72. STARTUP-LIKE DETAILS

Make the product feel like a real startup.

Use copy such as:

> Your AI financial research room.

> Research less. Understand more.

> From market movement to evidence in minutes.

Potential navigation:

```text
SignalRoom

Dashboard
Research
Watchlist
Briefings

Help
Settings
```

Primary action:

> Investigate

Secondary:

> Listen

Evidence CTA:

> Show evidence

Avoid overly generic words like “Generate AI Report”.

---

# 73. BACKEND CONFIGURATION

Use Pydantic Settings.

Example:

```text
AWS_REGION
DYNAMODB_TABLE_PREFIX

S3_BUCKET

COGNITO_USER_POOL_ID
COGNITO_APP_CLIENT_ID
COGNITO_REGION

OPENAI_API_KEY
OPENAI_MODEL

GEMINI_API_KEY
GEMINI_MULTIMODAL_MODEL
GEMINI_TRANSCRIBE_MODEL
GEMINI_TTS_MODEL

ALPHAVANTAGE_API_KEY
FRED_API_KEY
SEC_USER_AGENT

SES_FROM_EMAIL

APP_BASE_URL
FRONTEND_URL
```

Validate required settings at startup.

Optional providers should not crash startup.

---

# 74. FRONTEND CONFIGURATION

Only expose safe configuration to Vite:

```text
VITE_API_BASE_URL
VITE_COGNITO_USER_POOL_ID
VITE_COGNITO_CLIENT_ID
VITE_COGNITO_REGION
VITE_APP_ENV
VITE_DEMO_MODE
```

Never expose:

```text
OPENAI_API_KEY
GEMINI_API_KEY
ALPHAVANTAGE_API_KEY
FRED_API_KEY
AWS secret credentials
```

---

# 75. DOCKER

Create:

```text
backend/Dockerfile
frontend/Dockerfile
```

Backend should run FastAPI with a production server.

Worker can use the same backend image with a different command.

Example conceptual commands:

```text
API:
uvicorn app.main:app

WORKER:
python -m app.workers.sqs_worker

SCHEDULED:
python -m app.workers.daily_briefing_scheduler
```

Frontend can be built as static assets.

Use a multi-stage Docker build if useful.

---

# 76. LOCAL DEVELOPMENT

Create:

```text
docker-compose.yml
```

for convenient local development where reasonable.

Also provide:

```text
scripts/
  dev.sh
  test.sh
  lint.sh
  seed_demo.sh
  generate_demo_audio.py
  set_secrets.sh
  deploy.sh
```

Make scripts usable on Windows as much as practical.

Also include PowerShell equivalents for important setup scripts where helpful:

```text
scripts/set_secrets.ps1
scripts/deploy.ps1
```

---

# 77. TESTS

Backend:

* pytest
* unit tests
* integration tests with mocked providers
* agent output validation
* API authorization tests
* repository tests
* financial calculation tests

Frontend:

* Vitest
* React Testing Library

Test:

* login guard
* watchlist
* investigation creation
* investigation states
* chart rendering
* error states

Do not call real paid APIs during tests.

Use mocked adapters.

---

# 78. CODE QUALITY

Use:

* Ruff
* mypy
* pytest
* ESLint
* Prettier

Keep code modular.

Avoid files > approximately 500 lines unless justified.

No giant agent file containing every agent.

No giant React component containing an entire page.

Use interfaces and dependency injection where appropriate.

---

# 79. CI

Create GitHub Actions for:

```text
backend:
  lint
  type check
  tests

frontend:
  lint
  type check
  build

terraform:
  fmt check
  validate
```

Do not store AWS credentials in GitHub secrets as long-lived access keys if avoidable.

Use AWS OIDC only if implementing deployment automation.

---

# 80. README

Write an excellent `README.md`.

It must include:

## SignalRoom AI

### Product

What it is.

### Problem

What problem it solves.

### Solution

How the AI research team works.

### Architecture

Include a Mermaid diagram.

### Agent architecture

Explain every agent.

### Multimodal flow

Explain:

```text
Text
Image
PDF
Audio
Market Data
News
   ↓
Agents
   ↓
Synthesis
   ↓
Text
Charts
Evidence Graph
Audio
Email
```

### Data sources

Explain exactly:

* yfinance
* SEC
* GDELT
* optional Alpha Vantage
* optional FRED

State which are keyless and which require free keys.

### AI models

Explain:

* GPT-6 Luna
* Gemini 3.8 Flash
* Gemini 3.5 Transcribe
* Gemini 3.8 Flash TTS

### AWS architecture

### Terraform

### Local setup

### AWS deployment

### Environment variables

### Secrets Manager

### Demo

### Screenshots

Add screenshot placeholders or instructions for adding actual screenshots.

### Limitations

### Financial disclaimer

### Future roadmap

---

# 81. TECHNICAL ARCHITECTURE DOCUMENT

Create:

```text
docs/
  architecture.md
  agents.md
  data-sources.md
  aws.md
  local-development.md
  demo.md
  compliance.md
  cost-analysis.md
```

`docs/cost-analysis.md` should estimate:

* AWS infrastructure
* AI inference
* TTS
* transcription
* external APIs

Do not invent exact current AWS prices.

Where pricing depends on region/usage, say so and link to the relevant AWS pricing page in the documentation.

---

# 82. ARCHITECTURE DIAGRAM

Create a Mermaid diagram such as:

```text
flowchart TD
    User --> React
    React --> Cognito
    React --> FastAPI

    FastAPI --> DynamoDB
    FastAPI --> S3
    FastAPI --> SQS

    SQS --> Worker

    Worker --> Orchestrator

    Orchestrator --> MarketAgent
    Orchestrator --> NewsAgent
    Orchestrator --> FinancialAgent
    Orchestrator --> SentimentAgent
    Orchestrator --> EventAgent
    Orchestrator --> RiskAgent
    Orchestrator --> EvidenceAgent
    Orchestrator --> SynthesisAgent

    MarketAgent --> Yahoo
    NewsAgent --> GDELT
    FinancialAgent --> SEC
    FinancialAgent --> UserFiles

    UserFiles --> GeminiVision
    UserAudio --> GeminiTranscribe

    SynthesisAgent --> GPT6Luna
    BriefingAgent --> GeminiTTS

    Worker --> SES

    EventBridge --> ScheduledWorker
```

Adapt it to the actual implementation.

---

# 83. DEMO SCRIPT

Create:

```text
docs/demo.md
```

The ideal 3-5 minute demo should be:

### 1

Open landing page.

### 2

Sign in.

### 3

Show dashboard.

### 4

Select NVIDIA.

### 5

Click:

> Why?

### 6

Show real agent progress.

### 7

Show final explanation.

### 8

Open evidence graph.

### 9

Open chart and sentiment timeline.

### 10

Upload a synthetic earnings-call audio file.

### 11

Show transcription.

### 12

Ask:

> Does this change the thesis?

### 13

Show updated synthesis.

### 14

Click:

> Listen

### 15

Show generated audio.

### 16

Show daily email preview.

The demo should make the multimodal orchestration obvious.

---

# 84. DO NOT OVERENGINEER

We are building an MVP for an academic FinTech startup assignment.

Do NOT add unnecessary infrastructure.

Avoid:

* Kubernetes
* microservices everywhere
* Kafka
* Redis
* service mesh
* distributed tracing infrastructure
* complex vector databases
* custom ML training
* model fine-tuning
* trading execution
* brokerage integrations
* payments
* blockchain
* crypto wallets

The value comes from:

> **multi-agent orchestration + multimodality + usable product**

not infrastructure complexity.

---

# 85. DO NOT USE TRAINING DATASETS

Do not create or train a custom financial model.

The application should work from:

* live/free public data
* user-uploaded data
* structured calculations
* foundation models

No custom training pipeline is necessary.

---

# 86. IMPORTANT MODEL SAFETY / ACCURACY RULES

The agents must not:

* invent prices
* invent earnings
* invent news
* invent source links
* invent financial statements
* invent article quotes
* claim statistical certainty
* claim causal certainty without evidence
* produce personalized buy/sell instructions

When information is missing:

```text
Not enough evidence available.
```

is preferable to hallucination.

Always surface source evidence for important claims.

---

# 87. AGENT EXECUTION VISIBILITY

The UI should visibly communicate the AI architecture.

For each completed agent:

```text
✓ Market Agent
Analyzed price, volatility and volume

✓ News Agent
Reviewed 32 relevant articles

✓ Financial Agent
Analyzed latest available financial data

✓ Risk Agent
Identified 3 material risk themes

✓ Evidence Agent
Cross-checked 9 supporting sources

✓ Synthesis Agent
Generated final explanation
```

This is important for the academic presentation because the evaluator must be able to SEE the multi-agent architecture.

---

# 88. MODEL COST OPTIMIZATION

Avoid unnecessary LLM calls.

Rules:

* deterministic calculations should happen in Python
* retrieve data before calling the LLM
* deduplicate news before summarization
* summarize clusters, not individual articles repeatedly
* cache repeated analysis
* reuse investigation context for follow-up questions
* use TTS only when requested or daily briefing audio is enabled
* do not regenerate audio if unchanged

The architecture must make model usage observable.

Store per-investigation:

```text
model
provider
input_tokens if available
output_tokens if available
latency
```

Do not store prompt content containing secrets.

---

# 89. PROVIDER FALLBACKS

Implement provider adapters.

If an optional provider is unavailable:

```text
Alpha Vantage unavailable
↓
Use GDELT/yfinance/SEC
```

If audio is not provided:

```text
audio analysis unavailable
```

but the rest of the investigation continues.

The system should degrade gracefully.

---

# 90. “AVAILABLE MODALITIES” PANEL

On the research page, make capabilities obvious.

Example:

```text
Research with

✓ Text
✓ Market data
✓ News
✓ PDF
✓ Image
✓ Audio
```

The user can drag and drop files.

Do not force users to understand the agent architecture.

The product should feel simple even though the backend is complex.

---

# 91. RESEARCH INPUT UI

Build a premium composer:

```text
What do you want to understand?

[ Why did NVIDIA fall today?                 ]

+ Add PDF
+ Add image
+ Add audio

[ Investigate ]
```

After clicking:

> Investigate

show:

```text
SignalRoom is assembling your research team...
```

This should be one of the central UX moments.

---

# 92. SETTINGS

Create:

```text
Account
Notifications
Daily Briefing
Watchlist
Data & Privacy
```

Daily briefing settings:

```text
[✓] Daily briefing
Time: 08:00
Timezone: Europe/Madrid

[✓] Email me the briefing

Voice:
Professional
```

Add delete-account/delete-data placeholders if not fully implementing account deletion.

At minimum, implement deletion of user investigation data if practical.

---

# 93. PRIVACY

Because this is a financial application:

* minimize stored personal data
* use private S3
* secure access by authenticated user
* do not expose files publicly
* do not log document/audio contents
* document provider data flows
* allow user deletion of uploaded files
* distinguish third-party AI processing from application storage

Since the academic MVP is not a regulated banking system, explicitly describe it as a prototype and avoid claiming regulatory certification.

---

# 94. FINAL REPOSITORY STRUCTURE

Aim approximately for:

```text
/
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── workflows/
│   │   ├── integrations/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── prompts/
│   │   ├── skills/
│   │   ├── schemas/
│   │   ├── models/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── terraform/
│   ├── modules/
│   │   ├── networking/
│   │   ├── ecr/
│   │   ├── ecs/
│   │   ├── alb/
│   │   ├── s3/
│   │   ├── cloudfront/
│   │   ├── cognito/
│   │   ├── dynamodb/
│   │   ├── sqs/
│   │   ├── eventbridge/
│   │   ├── secrets-manager/
│   │   ├── iam/
│   │   └── ses/
│   └── environments/
│       └── dev/
│
├── demo_data/
├── docs/
├── scripts/
├── .github/
│   └── workflows/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

Adapt this only where a better implementation requires it.

---

# 95. IMPLEMENTATION PROCESS

Now actually implement the project.

Follow this process internally:

### Step 1

Inspect the current repository.

### Step 2

Create the architecture and base folders.

### Step 3

Build backend configuration and models.

### Step 4

Build provider interfaces and implementations.

### Step 5

Build DynamoDB/S3 repositories.

### Step 6

Build LangGraph agents.

### Step 7

Build SQS worker.

### Step 8

Build FastAPI APIs.

### Step 9

Build authentication.

### Step 10

Build React frontend.

### Step 11

Build charts/evidence graph/progress UI.

### Step 12

Build daily briefing and TTS.

### Step 13

Build SES email.

### Step 14

Build Terraform.

### Step 15

Build demo data.

### Step 16

Run tests/lint/type checking/builds.

### Step 17

Fix failures.

### Step 18

Write documentation.

Do not stop after producing only the scaffolding.

---

# 96. QUALITY BAR

Before considering the task complete:

### Backend

```text
pytest
ruff
mypy
```

must pass.

### Frontend

```text
npm run lint
npm run build
npm test
```

must pass where configured.

### Terraform

```text
terraform fmt -check
terraform validate
```

must pass.

### Docker

Both images must build.

### API

FastAPI must expose functional OpenAPI docs.

### Demo

The application must be usable in demo mode even if external APIs are not available.

---

# 97. IMPORTANT: DO NOT LEAVE PSEUDOCODE

Do not write:

```python
# TODO: implement later
```

for core functionality.

Do not use fake:

```python
return {"summary": "AI analysis here"}
```

for production paths.

Use real provider calls behind adapters.

Use mocks only in:

* tests
* demo fallback

---

# 98. IMPORTANT: NO SECRET LEAKS

Before completion, scan the repository for:

```text
sk-
AIza
AWS_ACCESS_KEY
AWS_SECRET
password=
api_key=
```

and make sure no real credentials exist.

Never commit `.env`.

---

# 99. FINAL OUTPUT FROM YOU

After implementing, give me a concise final report containing:

1. What was implemented.
2. Repository structure.
3. How the agents work.
4. How asynchronous jobs work.
5. How scheduled briefings work.
6. How frontend/backend communicate.
7. How AWS is structured.
8. Which external data sources are used.
9. Which models are used.
10. Which secrets need to be created.
11. Exact local development commands.
12. Exact AWS deployment commands.
13. Tests/build status.
14. Any remaining configuration that requires my credentials or AWS setup.

Most importantly:

**BUILD THE ACTUAL APPLICATION.**
