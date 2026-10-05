"""Persists real progress: every event corresponds to an agent that actually started/finished."""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.agents.base import AGENT_EVENT_TYPES, AGENT_LABELS
from app.models.status import InvestigationStatus, can_transition
from app.repositories.base import EventRepository, InvestigationRepository
from app.schemas.investigations import InvestigationEvent
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

ANALYSIS_PHASE = {"sentiment", "event_detection", "risk", "evidence"}
COLLECTION_PHASE = {"market", "news", "financial", "macro", "document", "vision", "audio", "video"}


class InvestigationDeleted(Exception):
    """The investigation was deleted by the user while the worker was running."""


class ProgressReporter:
    def __init__(
        self,
        investigation_id: str,
        investigations: InvestigationRepository,
        events: EventRepository,
    ) -> None:
        self.investigation_id = investigation_id
        self._investigations = investigations
        self._events = events
        self._lock = threading.Lock()
        self.total_units = 1
        self.done_units = 0

    def set_plan(self, agents: list[str], with_audio: bool) -> None:
        # orchestrator (already done) + planned agents + optional voice
        self.total_units = 1 + len(agents) + (1 if with_audio else 0)
        self.done_units = 1

    @property
    def progress(self) -> int:
        return min(95, int(self.done_units / max(self.total_units, 1) * 95))

    def _update_record(self, **fields: Any) -> str:
        record = self._investigations.get(self.investigation_id)
        if record is None:
            raise InvestigationDeleted(self.investigation_id)
        target = fields.get("status")
        if target and not can_transition(record.status, target):
            fields.pop("status")
        for key, value in fields.items():
            setattr(record, key, value)
        record.updated_at = utc_now_iso()
        self._investigations.put(record)
        return record.status

    def event(
        self,
        event_type: str,
        message: str,
        *,
        agent: str | None = None,
        status: str | None = None,
        **metadata: Any,
    ) -> None:
        with self._lock:
            fields: dict[str, Any] = {"progress": self.progress, "status_message": message}
            if status:
                fields["status"] = status
            if agent is not None:
                fields["current_agent"] = agent
            current_status = self._update_record(**fields)
            self._events.append(
                InvestigationEvent(
                    investigation_id=self.investigation_id,
                    seq=0,
                    timestamp=utc_now_iso(),
                    event_type=event_type,
                    message=message,
                    agent=agent,
                    progress=self.progress,
                    status=current_status,
                    metadata=metadata,
                )
            )

    def status(self, status: InvestigationStatus, message: str) -> None:
        self.event(status.value, message, status=status.value)

    def agent_started(self, agent: str) -> None:
        phase_status: str | None = None
        if agent in COLLECTION_PHASE:
            phase_status = InvestigationStatus.COLLECTING_DATA.value
        elif agent in ANALYSIS_PHASE:
            phase_status = InvestigationStatus.ANALYZING.value
        elif agent == "synthesis":
            phase_status = InvestigationStatus.SYNTHESIZING.value
        elif agent == "voice":
            phase_status = InvestigationStatus.GENERATING_AUDIO.value
        label = AGENT_LABELS.get(agent, agent)
        self.event(
            AGENT_EVENT_TYPES.get(agent, agent),
            f"{label} started",
            agent=agent,
            status=phase_status,
            phase="started",
        )

    def agent_finished(self, agent: str, outcome: str, summary: str, duration_ms: int) -> None:
        with self._lock:
            self.done_units += 1
        label = AGENT_LABELS.get(agent, agent)
        self.event(
            AGENT_EVENT_TYPES.get(agent, agent),
            summary or f"{label} {outcome}",
            agent=agent,
            phase=outcome,
            label=label,
            duration_ms=duration_ms,
        )
