"""Video Agent — financial webinars / investor presentations (Gemini multimodal: audio + frames).

One model call reads the speech and the slides together; quotes are verified verbatim
against the returned transcript and the full transcript is stored privately in storage.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.guardrails import verbatim_quotes
from app.agents.sources import upload_source
from app.integrations.ai.base import AIError, AIUnavailableError, VideoInput
from app.integrations.storage.base import investigation_output_key
from app.prompts.loader import system_prompt
from app.schemas.agents import Transcript, VideoAnalysis, VideoFindings
from app.schemas.investigations import AttachmentRef

MAX_INLINE_VIDEO_BYTES = 40 * 1024 * 1024


class VideoAgent:
    name = "video"
    label = "Video Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        clips = [a for a in state.get("attachments", []) if a.kind == "video"]
        if not clips:
            raise AgentSkipped("No video attached")
        if not ctx.ai.available("vision"):
            raise AIUnavailableError("Video-capable model not configured")
        findings = [await self._process(clip, state, ctx) for clip in clips]  # sequential: heaviest calls
        sources = [upload_source("video", c.upload_id, c.filename) for c in clips]
        slides = sum(len(f.slides) for f in findings)
        segments = sum(f.segment_count for f in findings)
        return AgentOutput(
            {"videos": findings, "sources": sources},
            f"Analysed {len(findings)} video(s): {segments} speech segments and {slides} slides/charts",
        )

    async def _process(self, clip: AttachmentRef, state: dict[str, Any], ctx: AgentContext) -> VideoFindings:
        data = await asyncio.to_thread(ctx.storage.get_bytes, clip.storage_key)
        if len(data) > MAX_INLINE_VIDEO_BYTES:
            raise AIError("Video too large for analysis (max 40 MB)")
        analysis = await ctx.ai.structured(
            VideoAnalysis,
            system=system_prompt("video_agent", "earnings_analysis"),
            user=f"Asset in focus: {state.get('symbol') or 'unknown'}. Question: {state['question']}",
            videos=[VideoInput(data, clip.content_type)],
            role="vision",
            agent=self.name,
            purpose="video_analysis",
            max_tokens=16000,
            temperature=0.0,
        )
        transcript = Transcript(
            language=analysis.language, speakers=analysis.speakers, segments=analysis.segments
        )
        key = investigation_output_key(
            state["user_id"], state["investigation_id"], "transcripts", f"{clip.upload_id}.json"
        )
        await asyncio.to_thread(
            ctx.storage.put_bytes, key, transcript.model_dump_json().encode("utf-8"), "application/json"
        )
        spoken = "\n".join(s.text for s in analysis.segments)
        return VideoFindings(
            upload_id=clip.upload_id,
            filename=clip.filename,
            summary=analysis.summary,
            language=analysis.language,
            speakers=analysis.speakers or sorted({s.speaker for s in analysis.segments}),
            segment_count=len(analysis.segments),
            transcript_key=key,
            transcript_preview=analysis.segments[:6],
            slides=analysis.slides[:20],
            key_points=analysis.key_points,
            guidance=analysis.guidance,
            management_tone=analysis.management_tone,
            risks=analysis.risks,
            notable_quotes=verbatim_quotes(analysis.notable_quotes, spoken),
            source_id=f"src_video_{clip.upload_id}",
        )
