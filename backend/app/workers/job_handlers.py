"""Job payload validation and dispatch (shared by the SQS worker and the local worker)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.config.logging import job_id_var, user_ref_var
from app.container import Container
from app.utils.ids import user_ref

logger = logging.getLogger(__name__)


class Job(BaseModel):
    job_type: Literal["investigation", "followup", "investigation_audio", "infographic", "briefing"]
    job_id: str
    user_id: str
    investigation_id: str | None = None
    followup_id: str | None = None
    briefing_id: str | None = None
    with_audio: bool = True
    send_email: bool = False
    delivery_key: str | None = None


class InvalidJob(Exception):
    """Malformed payload: acknowledge and drop (retrying cannot fix it)."""


def parse_job(body: dict[str, Any]) -> Job:
    try:
        job = Job.model_validate(body)
    except ValidationError as exc:
        raise InvalidJob(str(exc.errors()[:2])) from exc
    if (
        job.job_type in ("investigation", "followup", "investigation_audio", "infographic")
        and not job.investigation_id
    ):
        raise InvalidJob("investigation_id is required")
    if job.job_type == "followup" and not job.followup_id:
        raise InvalidJob("followup_id is required")
    if job.job_type == "briefing" and not job.briefing_id:
        raise InvalidJob("briefing_id is required")
    return job


async def handle_job(c: Container, body: dict[str, Any]) -> None:
    job = parse_job(body)
    tokens = (job_id_var.set(job.job_id), user_ref_var.set(user_ref(job.user_id)))
    try:
        logger.info("job_started", extra={"job_type": job.job_type})
        if job.job_type == "investigation":
            from app.workflows.investigation_runner import run_investigation

            await run_investigation(c, job.investigation_id or "")
        elif job.job_type == "followup":
            from app.workflows.followup import run_followup

            await run_followup(c, job.investigation_id or "", job.followup_id or "")
        elif job.job_type == "investigation_audio":
            from app.workflows.media import run_investigation_audio

            await run_investigation_audio(c, job.investigation_id or "")
        elif job.job_type == "infographic":
            from app.workflows.media import run_infographic

            await run_infographic(c, job.investigation_id or "")
        elif job.job_type == "briefing":
            from app.workflows.briefing_flow import run_briefing

            await run_briefing(
                c,
                job.briefing_id or "",
                with_audio=job.with_audio,
                send_email=job.send_email,
                delivery_key=job.delivery_key,
            )
        logger.info("job_finished", extra={"job_type": job.job_type})
    finally:
        job_id_var.reset(tokens[0])
        user_ref_var.reset(tokens[1])
