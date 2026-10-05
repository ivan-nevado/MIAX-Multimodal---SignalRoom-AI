"""Daily / on-demand briefing job: Briefing Agent → (Voice Agent) → store → (SES email).

Idempotent per briefing: a completed briefing is not regenerated and an email is
never sent twice (email_status + delivery marker are checked before sending).
"""

from __future__ import annotations

import logging

from app.agents.briefing import BriefingAgent, speech_script
from app.agents.voice import narrate
from app.container import Container
from app.integrations.ai.base import UsageTracker
from app.integrations.storage.base import briefing_output_key
from app.services.email_renderer import render_briefing_email
from app.services.watchlist_service import DEMO_WATCHLIST
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)


async def run_briefing(
    c: Container, briefing_id: str, *, with_audio: bool, send_email: bool, delivery_key: str | None = None
) -> None:
    b = c.repos.briefings.get(briefing_id)
    if b is None:
        return
    if b.status != "completed":
        b.status = "running"
        c.repos.briefings.put(b)
        items = c.repos.watchlists.list(b.user_id)
        watchlist: list[tuple[str, str, str]] = [
            (i.symbol, i.display_name, str(i.asset_type)) for i in items
        ] or [(s, n, t) for s, n, t in DEMO_WATCHLIST]
        tracker = UsageTracker()
        ctx = c.agent_context(tracker)
        try:
            draft = await BriefingAgent().run(watchlist, ctx)
        except Exception as exc:
            logger.exception("briefing_failed", extra={"error_type": type(exc).__name__})
            b.status, b.error = "failed", "Could not prepare the briefing. Please retry."
            c.repos.briefings.put(b)
            if delivery_key:
                c.repos.deliveries.release(delivery_key)  # allow the next scheduler run to retry
            return
        out = draft.output
        b.headline, b.greeting, b.summary = out.headline, out.greeting, out.summary
        b.sections, b.risk_flags, b.macro_events = out.sections, out.risk_flags, out.macro_events
        b.top_events = [s.title for s in out.sections]
        b.watchlist_moves = draft.moves
        b.sources = list({s.id: s for s in draft.sources}.values())
        b.ai_narrative_available = draft.ai_narrative_available
        if with_audio and b.audio_key is None and ctx.ai.available("tts"):
            b.audio_status = "pending"
            c.repos.briefings.put(b)
            key = briefing_output_key(b.user_id, b.briefing_id, "briefing.wav")
            try:
                b.audio_duration_seconds = await narrate(ctx.ai, c.storage, speech_script(out), key)
                b.audio_key, b.audio_status = key, "ready"
            except Exception as exc:
                logger.warning("briefing_audio_failed", extra={"error_type": type(exc).__name__})
                b.audio_status = "failed"
        elif not with_audio:
            b.audio_status = "none"
        b.model_usage = tracker.records
        b.status = "completed"
        b.completed_at = utc_now_iso()
        c.repos.briefings.put(b)

    if send_email and b.email_status not in ("sent", "skipped"):
        _send_email(c, briefing_id, delivery_key)


def _send_email(c: Container, briefing_id: str, delivery_key: str | None) -> None:
    b = c.repos.briefings.get(briefing_id)
    if b is None:
        return
    if delivery_key and (c.repos.deliveries.get(delivery_key) or {}).get("email_sent"):
        b.email_status = "sent"
        c.repos.briefings.put(b)
        return
    user = c.repos.users.get(b.user_id)
    if user is None or not user.email:
        b.email_status = "skipped"
        c.repos.briefings.put(b)
        return
    audio_url = c.storage.presign_get(b.audio_key, 3600 * 24 * 7) if b.audio_key else None
    subject, html, text = render_briefing_email(b, frontend_url=c.settings.frontend_url, audio_url=audio_url)
    try:
        message_id = c.email.send(to=user.email, subject=subject, html=html, text=text)
        b.email_status = "sent"
        if delivery_key:
            c.repos.deliveries.update(delivery_key, {"email_sent": True, "message_id": message_id})
    except Exception as exc:
        logger.warning("briefing_email_failed", extra={"error_type": type(exc).__name__})
        b.email_status = "failed"
    c.repos.briefings.put(b)
