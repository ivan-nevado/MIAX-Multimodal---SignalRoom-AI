"""Follow-up questions reuse the stored investigation context and run only the minimal new work."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.audio import AudioAgent
from app.agents.base import AGENT_LABELS, AgentContext, AgentSkipped
from app.agents.document import DocumentAgent
from app.agents.evidence_pack import build_evidence_pack, known_evidence_ids
from app.agents.financial import FinancialAgent
from app.agents.guardrails import clean_narrative, filter_ids
from app.agents.news import NewsAgent
from app.agents.video import VideoAgent
from app.agents.vision import VisionAgent
from app.container import Container
from app.integrations.ai.base import AIError, UsageTracker
from app.prompts.loader import system_prompt
from app.schemas.agents import FollowUpLLMOutput
from app.schemas.investigations import InvestigationEvent, InvestigationRecord
from app.utils.time import utc_now_iso
from app.workflows.state import merge_sources

logger = logging.getLogger(__name__)

_FIN_RE = re.compile(r"earnings|revenue|margin|financial|report|results|guidance|balance|debt|cash", re.I)
_NEWS_RE = re.compile(r"news|latest|headline|today|announce|report", re.I)


def state_from_record(record: InvestigationRecord) -> dict[str, Any]:
    r = record.result
    assert r is not None
    return {
        "investigation_id": record.investigation_id,
        "user_id": record.user_id,
        "symbol": record.symbol,
        "asset_name": record.asset_name,
        "asset_type": record.asset_type,
        "question": record.question,
        "plan": record.plan,
        "market": r.market,
        "news": r.news,
        "financial": r.financial,
        "macro": r.macro,
        "sentiment": r.sentiment,
        "events": r.events,
        "risks": r.risks,
        "documents": list(r.documents),
        "images": list(r.images),
        "audio": list(r.audio),
        "videos": list(r.videos),
        "sources": list(r.sources),
    }


def plan_followup(question: str, state: dict[str, Any], new_kinds: set[str]) -> list[str]:
    """Minimal new work: analyse new files; fetch data only if missing and relevant to the question."""
    agents = [
        a
        for kind, a in (("document", "document"), ("image", "vision"), ("audio", "audio"), ("video", "video"))
        if kind in new_kinds
    ]
    if state.get("symbol"):
        fin = state.get("financial")
        if _FIN_RE.search(question) and fin is None and state.get("asset_type") in ("equity", "etf", None):
            agents.append("financial")
        if _NEWS_RE.search(question) and state.get("news") is None:
            agents.append("news")
    return agents


async def run_followup(c: Container, investigation_id: str, followup_id: str) -> None:
    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None:
        return
    fu = next((f for f in record.followups if f.followup_id == followup_id), None)
    if fu is None or fu.status == "completed":
        return
    fu.status = "running"
    c.repos.investigations.put(record)

    def event(event_type: str, message: str, agent: str | None = None) -> None:
        c.repos.events.append(
            InvestigationEvent(
                investigation_id=investigation_id,
                seq=0,
                timestamp=utc_now_iso(),
                event_type=event_type,
                message=message,
                agent=agent,
                metadata={"followup_id": followup_id},
            )
        )

    tracker = UsageTracker()
    ctx: AgentContext = c.agent_context(tracker)
    state = state_from_record(record)
    new_attachments = [a for a in record.attachments if a.upload_id in fu.upload_ids]
    plan = plan_followup(fu.question, state, {a.kind for a in new_attachments})
    event(
        "followup_running",
        "Reviewing existing evidence"
        + (f" and running {', '.join(AGENT_LABELS[a] for a in plan)}" if plan else ""),
    )

    agents: dict[str, Any] = {
        "document": DocumentAgent(),
        "vision": VisionAgent(),
        "audio": AudioAgent(),
        "video": VideoAgent(),
        "financial": FinancialAgent(),
        "news": NewsAgent(),
    }
    agent_state = {**state, "question": fu.question, "attachments": new_attachments}
    ran: list[str] = []
    for name in plan:
        event("followup_agent", f"{AGENT_LABELS[name]} started", agent=name)
        try:
            out = await agents[name].run(agent_state, ctx)
        except AgentSkipped:
            continue
        except Exception as exc:
            logger.warning("followup_agent_failed", extra={"agent": name, "error_type": type(exc).__name__})
            event("followup_agent", f"{AGENT_LABELS[name]} could not complete", agent=name)
            continue
        for key, value in out.update.items():
            if key == "sources":
                state["sources"] = merge_sources(state["sources"], value)
            elif key in ("documents", "images", "audio", "videos"):
                state[key] = [*state.get(key, []), *value]
            else:
                state[key] = value
        ran.append(name)
        event("followup_agent", out.summary, agent=name)

    answer, evidence_ids = "Not enough evidence available to answer this follow-up.", []
    if ctx.ai.available("reasoning"):
        result = record.result
        payload = {
            "original_question": record.question,
            "follow_up_question": fu.question,
            "previous_summary": result.executive_summary,
            "drivers": [
                {
                    "driver_id": d.driver_id,
                    "name": d.name,
                    "contribution_pct": d.contribution_score,
                    "explanation": d.explanation,
                    "evidence_ids": d.evidence_ids,
                }
                for d in result.drivers
            ],
            "evidence": build_evidence_pack(state),
            "retrieved_passages": await c.search_index(tracker).passages(
                record.user_id, investigation_id, fu.question
            ),
            "previous_followups": [{"q": f.question, "a": f.answer} for f in record.followups if f.answer][
                -3:
            ],
        }
        try:
            out = await ctx.ai.structured(
                FollowUpLLMOutput,
                system=system_prompt("followup_agent", "financial_analysis", "market_analysis"),
                user=json.dumps(payload, default=str),
                agent="followup",
                purpose="followup_answer",
                max_tokens=1800,
            )
            answer = clean_narrative(out.answer)
            evidence_ids = filter_ids(out.evidence_ids, known_evidence_ids(state))
        except AIError as exc:
            logger.warning("followup_llm_failed", extra={"error_type": type(exc).__name__})
            answer = "The research analyst model is unavailable right now. Please retry."

    record = c.repos.investigations.get(investigation_id)
    if record is None or record.result is None:
        return
    for key in ("documents", "images", "audio", "videos", "sources"):
        setattr(record.result, key, state[key])
    if "financial" in ran:
        record.result.financial = state["financial"]
    if "news" in ran:
        record.result.news = state["news"]
    record.result.model_usage.extend(tracker.records)
    for f in record.followups:
        if f.followup_id == followup_id:
            f.status, f.answer, f.evidence_ids, f.agents_run = "completed", answer, evidence_ids, ran
            f.completed_at = utc_now_iso()
    record.updated_at = utc_now_iso()
    if ran:  # new files were analysed: make them searchable too
        await c.search_index(tracker).index_safely(record)
    c.repos.investigations.put(record)
    event("followup_completed", "Follow-up answered")
