---
name: earnings_analysis
purpose: Analyse earnings-call transcripts and earnings documents.
---
# Earnings analysis

**When to use:** Audio Agent (after transcription) and Document Agent for earnings releases.

**Outputs:** summary, key points, guidance, management tone, risks, ≤3 verbatim quotes.

**Rules**
- Quotes must be copied verbatim from the transcript (a validator drops non-matching quotes).
- Separate reported results from guidance and from analyst questions.
- Management tone is a qualitative label: confident, cautious, defensive, mixed, neutral.
- Never invent figures not present in the transcript.

References: `references/earnings-call-structure.md`.
