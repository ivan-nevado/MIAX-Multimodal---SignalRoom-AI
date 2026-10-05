"""Document Agent — PDF → text extraction → relevant pages → Gemini vision on table/chart pages.

Never sends a whole annual report to a model: page count is detected, text is
extracted, the most relevant pages are selected and only those are analysed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import upload_source
from app.integrations.ai.base import AIError, ImageInput
from app.prompts.loader import system_prompt
from app.schemas.agents import DocumentFindings, DocumentLLMOutput, PageVisualAnalysis
from app.schemas.common import Model
from app.schemas.investigations import AttachmentRef
from app.skills.loader import load_reference
from app.utils.pdf import extract_pdf_text, is_table_heavy, render_pages, select_relevant_pages

logger = logging.getLogger(__name__)

TEXT_PAGES = 8
TEXT_CHAR_BUDGET = 24000


class PageVisualBatch(Model):
    pages: list[PageVisualAnalysis]


class DocumentAgent:
    name = "document"
    label = "Document Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        docs = [a for a in state.get("attachments", []) if a.kind == "document"]
        if not docs:
            raise AgentSkipped("No document attached")
        results = await asyncio.gather(*(self._analyse(doc, state["question"], ctx) for doc in docs))
        findings = [r for r in results if r is not None]
        sources = [upload_source("document", d.upload_id, d.filename) for d in docs]
        pages = sum(len(f.pages_analyzed) for f in findings)
        total = sum(f.page_count for f in findings)
        return AgentOutput(
            {"documents": findings, "sources": sources},
            f"Analyzed {pages} relevant pages out of {total} in {len(findings)} document(s)",
        )

    async def _analyse(self, doc: AttachmentRef, question: str, ctx: AgentContext) -> DocumentFindings:
        data = await asyncio.to_thread(ctx.storage.get_bytes, doc.storage_key)
        content = await asyncio.to_thread(extract_pdf_text, data)
        relevant = select_relevant_pages(content, question, TEXT_PAGES)
        findings = DocumentFindings(
            upload_id=doc.upload_id,
            filename=doc.filename,
            page_count=content.page_count,
            text_chars=content.total_chars,
            source_id=f"src_document_{doc.upload_id}",
        )

        # 1) Text pass (cheap reasoning model) on the relevant pages only.
        excerpt, used = "", []
        for page in relevant:
            chunk = f"\n[page {page.number}]\n{page.text}"
            if len(excerpt) + len(chunk) > TEXT_CHAR_BUDGET:
                break
            excerpt += chunk
            used.append(page.number)
        if excerpt.strip() and ctx.ai.available("reasoning"):
            try:
                out = await ctx.ai.structured(
                    DocumentLLMOutput,
                    system=system_prompt("financial_agent", "financial_analysis")
                    + "\n\n"
                    + load_reference("financial_analysis", "accounting.md"),
                    user=json.dumps(
                        {
                            "question": question,
                            "filename": doc.filename,
                            "page_count": content.page_count,
                            "excerpt": excerpt,
                        }
                    ),
                    agent=self.name,
                    purpose="document_text",
                    max_tokens=1800,
                )
                findings.summary, findings.key_facts = out.summary, out.key_facts
                findings.risks, findings.guidance = out.risks, out.guidance
            except AIError as exc:
                logger.warning("document_text_failed", extra={"error_type": type(exc).__name__})

        # 2) Vision pass only where text extraction loses structure (tables/charts/scans).
        visual_candidates = [p.number for p in relevant if is_table_heavy(p)]
        if not content.total_chars:
            visual_candidates = [
                p.number for p in content.pages[: ctx.settings.max_document_pages_for_vision]
            ]
        visual_candidates = visual_candidates[: ctx.settings.max_document_pages_for_vision]
        if visual_candidates and ctx.ai.available("vision"):
            try:
                rendered = await asyncio.to_thread(render_pages, data, visual_candidates)
                batch = await ctx.ai.structured(
                    PageVisualBatch,
                    system=system_prompt("document_vision", "financial_analysis"),
                    user=f"Pages attached in order: {[n for n, _ in rendered]}. Question: {question}",
                    images=[ImageInput(img, "image/jpeg") for _, img in rendered],
                    role="vision",
                    agent=self.name,
                    purpose="document_vision",
                    max_tokens=2500,
                )
                findings.visual_pages = batch.pages
            except AIError as exc:
                logger.warning("document_vision_failed", extra={"error_type": type(exc).__name__})
        findings.pages_analyzed = sorted(set(used) | {p.page for p in findings.visual_pages})
        if not findings.summary and findings.visual_pages:
            findings.summary = " ".join(p.description for p in findings.visual_pages[:2])
        return findings
