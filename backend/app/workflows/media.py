"""On-demand media jobs for a completed investigation: audio briefing (TTS) and visual brief (image model)."""

from __future__ import annotations

import asyncio
import logging

from app.agents.voice import investigation_script, narrate
from app.container import Container
from app.integrations.ai.base import UsageTracker
from app.integrations.storage.base import investigation_output_key
from app.prompts.loader import load_prompt
from app.schemas.investigations import InvestigationRecord

logger = logging.getLogger(__name__)


async def run_investigation_audio(c: Container, investigation_id: str) -> None:
    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None or record.audio_status == "ready":
        return
    tracker = UsageTracker()
    ai = c.ai.with_tracker(tracker)
    r = record.result
    script = investigation_script(
        record.asset_name or record.symbol or "your research question",
        r.executive_summary,
        "",
        [(d.name, d.contribution_score, d.explanation) for d in r.drivers],
        r.what_to_watch,
    )
    key = investigation_output_key(record.user_id, investigation_id, "audio", "brief.wav")
    try:
        await narrate(ai, c.storage, script, key)
        status = "ready"
    except Exception as exc:
        logger.warning("investigation_audio_failed", extra={"error_type": type(exc).__name__})
        status = "failed"
    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None:
        return
    record.audio_status = status  # type: ignore[assignment]
    record.audio_key = key if status == "ready" else None
    record.result.model_usage.extend(tracker.records)
    c.repos.investigations.put(record)


def infographic_prompt(record: InvestigationRecord) -> str:
    r = record.result
    assert r is not None
    lines = [load_prompt("infographic"), "", "Content to render:"]
    title = record.asset_name or record.symbol or "Research brief"
    lines.append(f'- Title: "{title}"')
    if r.market and r.market.metrics.move_pct is not None:
        lines.append(f'- Big number: "{r.market.metrics.move_pct:+.1f}%" with caption "latest session"')
    if r.drivers:
        lines.append('- Section label: "Why? Evidence-weighted contribution"')
        for d in r.drivers[:3]:
            lines.append(f'- Bar: "{d.name[:40]}" = {d.contribution_score:.0f}%')
    if r.risks and r.risks.items:
        top = r.risks.items[0]
        lines.append(f'- Risk chip: "{top.risk.title()} risk: {top.level}"')
    lines.append('- Brand mark top-left: "SignalRoom"')
    return "\n".join(lines)


async def run_infographic(c: Container, investigation_id: str) -> None:
    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None or record.infographic_status == "ready":
        return
    tracker = UsageTracker()
    ai = c.ai.with_tracker(tracker)
    key = investigation_output_key(record.user_id, investigation_id, "images", "visual-brief.png")
    try:
        data, mime = await ai.image(infographic_prompt(record))
        await asyncio.to_thread(c.storage.put_bytes, key, data, mime)
        status = "ready"
    except Exception as exc:
        logger.warning("infographic_failed", extra={"error_type": type(exc).__name__})
        status = "failed"
    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None:
        return
    record.infographic_status = status  # type: ignore[assignment]
    record.infographic_key = key if status == "ready" else None
    record.result.model_usage.extend(tracker.records)
    c.repos.investigations.put(record)
