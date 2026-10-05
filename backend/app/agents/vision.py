"""Vision Agent — chart screenshots, financial tables, slides (Gemini multimodal)."""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import upload_source
from app.integrations.ai.base import AIUnavailableError, ImageInput
from app.prompts.loader import system_prompt
from app.schemas.agents import ImageAnalysis, ImageFindings
from app.schemas.investigations import AttachmentRef
from app.utils.images import preprocess_image


class VisionAgent:
    name = "vision"
    label = "Vision Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        images = [a for a in state.get("attachments", []) if a.kind == "image"]
        if not images:
            raise AgentSkipped("No image attached")
        if not ctx.ai.available("vision"):
            raise AIUnavailableError("Vision model not configured")
        findings = await asyncio.gather(*(self._analyse(img, state, ctx) for img in images))
        sources = [upload_source("image", i.upload_id, i.filename) for i in images]
        kinds = ", ".join(sorted({f.image_type.replace("_", " ") for f in findings}))
        return AgentOutput(
            {"images": list(findings), "sources": sources}, f"Interpreted {len(findings)} image(s): {kinds}"
        )

    async def _analyse(self, att: AttachmentRef, state: dict[str, Any], ctx: AgentContext) -> ImageFindings:
        raw = await asyncio.to_thread(ctx.storage.get_bytes, att.storage_key)
        data, mime = await asyncio.to_thread(preprocess_image, raw)
        context = f"Asset in focus: {state.get('symbol') or 'unknown'} ({state.get('asset_name') or 'n/a'}). Question: {state['question']}"
        analysis = await ctx.ai.structured(
            ImageAnalysis,
            system=system_prompt("vision_agent", "market_analysis"),
            user=context,
            images=[ImageInput(data, mime)],
            role="vision",
            agent=self.name,
            purpose="image_analysis",
            max_tokens=1500,
        )
        return ImageFindings(
            **analysis.model_dump(),
            upload_id=att.upload_id,
            filename=att.filename,
            source_id=f"src_image_{att.upload_id}",
        )
