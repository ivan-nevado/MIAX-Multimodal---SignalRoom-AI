"""Audio Agent — transcription (Gemini) → speaker segments → earnings analysis (GPT reasoning).

The full transcript is stored as a private object in storage; the investigation
record keeps only metadata and a short preview (no unnecessary copies).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.guardrails import verbatim_quotes
from app.agents.sources import upload_source
from app.integrations.ai.base import AIError, AIUnavailableError, AudioInput
from app.integrations.storage.base import investigation_output_key
from app.prompts.loader import system_prompt
from app.schemas.agents import AudioFindings, EarningsCallAnalysis, Transcript
from app.schemas.investigations import AttachmentRef
from app.skills.loader import load_reference

logger = logging.getLogger(__name__)

MAX_INLINE_AUDIO_BYTES = 25 * 1024 * 1024
TRANSCRIPT_CHAR_BUDGET = 40000


def transcript_text(t: Transcript) -> str:
    return "\n".join(f"{s.speaker}: {s.text}" for s in t.segments)


class AudioAgent:
    name = "audio"
    label = "Audio Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        clips = [a for a in state.get("attachments", []) if a.kind == "audio"]
        if not clips:
            raise AgentSkipped("No audio attached")
        if not ctx.ai.available("transcription"):
            raise AIUnavailableError("Transcription model not configured")
        findings = []
        for clip in clips:  # sequential: audio calls are the heaviest
            findings.append(await self._process(clip, state, ctx))
        sources = [upload_source("audio", c.upload_id, c.filename) for c in clips]
        segments = sum(f.segment_count for f in findings)
        speakers = len({s for f in findings for s in f.speakers})
        return AgentOutput(
            {"audio": findings, "sources": sources},
            f"Transcribed {len(findings)} recording(s): {segments} segments, {speakers} speaker(s)",
        )

    async def _process(self, clip: AttachmentRef, state: dict[str, Any], ctx: AgentContext) -> AudioFindings:
        data = await asyncio.to_thread(ctx.storage.get_bytes, clip.storage_key)
        if len(data) > MAX_INLINE_AUDIO_BYTES:
            raise AIError("Audio file too large for inline transcription (max 25 MB)")
        transcript = await ctx.ai.structured(
            Transcript,
            system=system_prompt("transcription"),
            user="Transcribe this recording.",
            audio=[AudioInput(data, clip.content_type)],
            role="transcription",
            agent=self.name,
            purpose="transcription",
            max_tokens=12000,
            temperature=0.0,
        )
        text = transcript_text(transcript)
        key = investigation_output_key(
            state["user_id"], state["investigation_id"], "transcripts", f"{clip.upload_id}.json"
        )
        await asyncio.to_thread(
            ctx.storage.put_bytes, key, transcript.model_dump_json().encode("utf-8"), "application/json"
        )
        findings = AudioFindings(
            upload_id=clip.upload_id,
            filename=clip.filename,
            language=transcript.language,
            speakers=transcript.speakers or sorted({s.speaker for s in transcript.segments}),
            segment_count=len(transcript.segments),
            transcript_key=key,
            transcript_preview=transcript.segments[:8],
            source_id=f"src_audio_{clip.upload_id}",
        )
        if text and ctx.ai.available("reasoning"):
            try:
                analysis = await ctx.ai.structured(
                    EarningsCallAnalysis,
                    system=system_prompt("earnings_agent", "earnings_analysis")
                    + "\n\n"
                    + load_reference("earnings_analysis", "earnings-call-structure.md"),
                    user=json.dumps(
                        {
                            "asset": state.get("symbol"),
                            "question": state["question"],
                            "transcript": text[:TRANSCRIPT_CHAR_BUDGET],
                        }
                    ),
                    agent=self.name,
                    purpose="earnings_analysis",
                    max_tokens=1800,
                )
                analysis.notable_quotes = verbatim_quotes(analysis.notable_quotes, text)
                findings.analysis = analysis
            except AIError as exc:
                logger.warning("earnings_analysis_failed", extra={"error_type": type(exc).__name__})
        return findings
