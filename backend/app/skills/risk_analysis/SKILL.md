---
name: risk_analysis
purpose: Qualitative, evidence-grounded risk assessment.
---
# Risk analysis

**When to use:** Risk Agent; risk flags in the daily briefing.

**Inputs:** evidence pack with ids (news clusters, market metrics, fundamentals, document/audio findings,
macro context).

**Outputs:** 1-6 risks `{risk, level LOW|MEDIUM|HIGH, reason, evidence_ids}`.

**Rules**
- Qualitative levels only; never probabilities.
- Each risk must cite evidence ids from the pack; unknown ids are discarded by the validator.
- Prefer specific reasons ("export licence requirements reported by 4 publishers") over generic ones.

References: `references/risk-framework.md`.
