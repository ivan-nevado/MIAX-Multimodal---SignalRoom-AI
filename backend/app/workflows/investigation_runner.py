"""Executes one investigation job end to end (called by the SQS/local worker).

Idempotent: a completed investigation is never re-run; a retried job restarts
cleanly and overwrites partial progress; audio is not regenerated if it exists.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from app.config.logging import investigation_id_var
from app.container import Container
from app.integrations.ai.base import UsageTracker
from app.integrations.market.base import MarketDataError
from app.models.status import InvestigationStatus
from app.schemas.investigations import InvestigationEvent, InvestigationRecord
from app.utils.time import utc_now_iso
from app.workflows.investigation_graph import build_investigation_graph
from app.workflows.progress import InvestigationDeleted, ProgressReporter
from app.workflows.result_builder import build_result

logger = logging.getLogger(__name__)

AGENT_DATA_NAMES = {
    "market": "Market data",
    "news": "the news provider",
    "financial": "financial data",
    "macro": "macro data",
}


def failure_message(final: dict[str, Any]) -> str:
    runs = {r.agent: r.status for r in final.get("agent_runs", [])}
    ok = [AGENT_DATA_NAMES[a] for a, s in runs.items() if s == "completed" and a in AGENT_DATA_NAMES]
    bad = [AGENT_DATA_NAMES[a] for a, s in runs.items() if s == "failed" and a in AGENT_DATA_NAMES]
    msg = "Could not complete the investigation."
    if ok and bad:
        msg += f" {ok[0].capitalize()} was available, but {' and '.join(bad)} {'was' if len(bad) == 1 else 'were'} unavailable."
    elif bad:
        msg += (
            f" {' and '.join(b.capitalize() for b in bad)} {'was' if len(bad) == 1 else 'were'} unavailable."
        )
    return msg + " You can retry."


def has_material(final: dict[str, Any]) -> bool:
    """At least one real piece of evidence was collected (empty news results do not count)."""
    news = final.get("news")
    return bool(
        final.get("market") is not None
        or (news is not None and news.articles)
        or any(final.get(k) for k in ("documents", "images", "audio", "videos"))
    )


def _fail(c: Container, record_id: str, message: str) -> None:
    record = c.repos.investigations.get(record_id)
    if record is None:
        return
    record.status, record.error, record.status_message = InvestigationStatus.FAILED.value, message, message
    record.current_agent = None
    record.updated_at = utc_now_iso()
    if record.audio_status == "pending":
        record.audio_status = "failed"
    c.repos.investigations.put(record)
    c.repos.events.append(
        InvestigationEvent(
            investigation_id=record_id,
            seq=0,
            timestamp=utc_now_iso(),
            event_type="failed",
            message=message,
            status="failed",
        )
    )


async def run_investigation(c: Container, investigation_id: str) -> None:
    token = investigation_id_var.set(investigation_id)
    try:
        await _run(c, investigation_id)
    finally:
        investigation_id_var.reset(token)


async def _run(c: Container, investigation_id: str) -> None:
    record: InvestigationRecord | None = c.repos.investigations.get(investigation_id)
    if record is None:
        logger.info("investigation_missing_skipping")
        return
    if record.status == InvestigationStatus.COMPLETED:
        logger.info("investigation_already_completed")
        return
    record.attempts += 1
    record.status = InvestigationStatus.RUNNING.value  # restart cleanly (queued/failed/stale running)
    record.error = None
    record.updated_at = utc_now_iso()
    c.repos.investigations.put(record)

    reporter = ProgressReporter(investigation_id, c.repos.investigations, c.repos.events)
    reporter.event(
        "running", "SignalRoom is assembling your research team...", status="running", agent="orchestrator"
    )

    if record.symbol and not record.asset_name:
        with contextlib.suppress(MarketDataError):
            record.asset_name = (await c.market.get_quote(record.symbol)).name

    tracker = UsageTracker()
    graph = build_investigation_graph(c.agent_context(tracker), reporter)
    initial: dict[str, Any] = {
        "investigation_id": investigation_id,
        "user_id": record.user_id,
        "symbol": record.symbol,
        "asset_name": record.asset_name,
        "asset_type": record.asset_type,
        "question": record.question,
        "attachments": record.attachments,
        "generate_audio": record.generate_audio and record.audio_key is None,
        "sources": [],
        "agent_runs": [],
        "warnings": [],
    }
    try:
        final: dict[str, Any] = await graph.ainvoke(initial)
    except InvestigationDeleted:
        logger.info("investigation_deleted_during_run")
        return
    except Exception as exc:
        logger.exception("investigation_graph_failed", extra={"error_type": type(exc).__name__})
        _fail(
            c,
            investigation_id,
            "Could not complete the investigation due to an internal error. You can retry.",
        )
        return

    if not has_material(final):
        _fail(c, investigation_id, failure_message(final))
        return

    result = build_result(final, tracker.records)
    record = c.repos.investigations.get(investigation_id)
    if record is None:
        return
    record.result = result
    record.plan = final.get("plan")
    record.asset_name = final.get("asset_name") or record.asset_name
    record.summary = result.executive_summary[:400]
    if final.get("audio_key"):
        record.audio_key, record.audio_status = final["audio_key"], "ready"
    elif record.generate_audio and record.audio_key is None:
        record.audio_status = "failed"
    search_tracker = UsageTracker()
    await c.search_index(search_tracker).index_safely(record)
    result.model_usage.extend(search_tracker.records)
    record.status = InvestigationStatus.COMPLETED.value
    record.progress = 100
    record.current_agent = None
    record.status_message = "Investigation complete"
    record.completed_at = record.updated_at = utc_now_iso()
    c.repos.investigations.put(record)
    c.repos.events.append(
        InvestigationEvent(
            investigation_id=investigation_id,
            seq=0,
            timestamp=utc_now_iso(),
            event_type="completed",
            message="Investigation complete",
            progress=100,
            status="completed",
            metadata={"cost_usd": tracker.total_cost, "model_calls": len(tracker.records)},
        )
    )
    logger.info(
        "investigation_completed", extra={"model_calls": len(tracker.records), "cost_usd": tracker.total_cost}
    )
