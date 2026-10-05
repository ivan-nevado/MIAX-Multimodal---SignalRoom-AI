"""Post-generation guardrails applied to every model-written narrative.

* Unknown evidence ids are removed (models cannot cite sources that do not exist).
* Unhedged causal language is softened ("caused" → "likely drove").
* Personalised buy/sell instructions are removed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_CAUSAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bwas caused by\b", re.I), "was likely driven by"),
    (re.compile(r"\bwere caused by\b", re.I), "were likely driven by"),
    (re.compile(r"\b(?<!likely )caused\b", re.I), "likely drove"),
]
_ADVICE_RE = re.compile(
    r"[^.!?]*\b(you should|we recommend|i recommend|consider (buying|selling)|(strong )?(buy|sell) (rating|signal|now)|"
    r"time to (buy|sell)|go long|go short)\b[^.!?]*[.!?]?",
    re.I,
)


def soften_causality(text: str) -> str:
    for pattern, replacement in _CAUSAL_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def strip_advice(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _ADVICE_RE.sub("", text)).strip()


def clean_narrative(text: str) -> str:
    return strip_advice(soften_causality(text or "")).strip()


def filter_ids(ids: Iterable[str], known: set[str]) -> list[str]:
    seen: list[str] = []
    for i in ids:
        if i in known and i not in seen:
            seen.append(i)
    return seen


def verbatim_quotes(quotes: Iterable[str], transcript_text: str) -> list[str]:
    """Keep only quotes that literally appear in the transcript (normalised whitespace/case)."""
    norm = " ".join(transcript_text.lower().split())
    kept = []
    for q in quotes:
        candidate = " ".join(q.strip().strip('"“”').lower().split())
        if candidate and candidate in norm:
            kept.append(q.strip().strip('"“”'))
    return kept
