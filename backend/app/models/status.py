"""Investigation state machine. Every transition is persisted by the investigation repository."""

from __future__ import annotations

from enum import StrEnum


class InvestigationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COLLECTING_DATA = "collecting_data"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({InvestigationStatus.COMPLETED, InvestigationStatus.FAILED})

_ALLOWED: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.QUEUED: frozenset({InvestigationStatus.RUNNING, InvestigationStatus.FAILED}),
    InvestigationStatus.RUNNING: frozenset(
        {InvestigationStatus.COLLECTING_DATA, InvestigationStatus.SYNTHESIZING, InvestigationStatus.FAILED}
    ),
    InvestigationStatus.COLLECTING_DATA: frozenset(
        {InvestigationStatus.ANALYZING, InvestigationStatus.SYNTHESIZING, InvestigationStatus.FAILED}
    ),
    InvestigationStatus.ANALYZING: frozenset({InvestigationStatus.SYNTHESIZING, InvestigationStatus.FAILED}),
    InvestigationStatus.SYNTHESIZING: frozenset(
        {InvestigationStatus.GENERATING_AUDIO, InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
    ),
    InvestigationStatus.GENERATING_AUDIO: frozenset(
        {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
    ),
    # A completed investigation can be re-opened by a follow-up or an on-demand audio job.
    InvestigationStatus.COMPLETED: frozenset({InvestigationStatus.RUNNING}),
    # A failed investigation can be retried (SQS redelivery or user retry).
    InvestigationStatus.FAILED: frozenset({InvestigationStatus.QUEUED, InvestigationStatus.RUNNING}),
}


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return True
    try:
        return InvestigationStatus(target) in _ALLOWED[InvestigationStatus(current)]
    except (ValueError, KeyError):
        return False


class InvalidTransitionError(ValueError):
    pass
