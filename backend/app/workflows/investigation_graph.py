"""LangGraph workflow for an investigation.

START → orchestrator ─┬─ market ───────┐
                      ├─ news ─────────┤
                      ├─ financial ────┤   (only the agents the orchestrator selected run;
                      ├─ macro ────────┼─→ collection_done ─┬─ sentiment ───────┐   collectors run in parallel)
                      ├─ document ─────┤                    └─ event_detection ─┴─→ risk → evidence → synthesis → [voice] → END
                      ├─ vision ───────┤
                      ├─ audio ────────┤
                      └─ video ────────┘
"""

from __future__ import annotations

import logging
import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.audio import AudioAgent
from app.agents.base import AGENT_LABELS, Agent, AgentContext, AgentOutput, AgentSkipped
from app.agents.document import DocumentAgent
from app.agents.events import EventDetectionAgent
from app.agents.evidence import EvidenceAgent
from app.agents.financial import FinancialAgent
from app.agents.macro import MacroAgent
from app.agents.market import MarketAgent
from app.agents.news import NewsAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.risk import RiskAgent
from app.agents.sentiment import SentimentAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.video import VideoAgent
from app.agents.voice import investigation_script, narrate
from app.integrations.ai.base import AIUnavailableError
from app.integrations.storage.base import investigation_output_key
from app.schemas.agents import AgentRun
from app.utils.time import utc_now_iso
from app.workflows.progress import InvestigationDeleted, ProgressReporter
from app.workflows.state import InvestigationState

logger = logging.getLogger(__name__)

COLLECTORS = ["market", "news", "financial", "macro", "document", "vision", "audio", "video"]


class VoiceAgent:
    name = "voice"
    label = "Voice Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        if not ctx.ai.available("tts"):
            raise AIUnavailableError("TTS model not configured")
        synthesis = state.get("synthesis")
        evidence = state.get("evidence")
        if synthesis is None:
            raise AgentSkipped("Nothing to narrate")
        drivers = []
        if evidence is not None:
            explanations = {d.driver_id: d.explanation for d in synthesis.drivers}
            drivers = [
                (d.name, d.contribution_score, explanations.get(d.driver_id, "")) for d in evidence.drivers
            ]
        script = investigation_script(
            state.get("asset_name") or state.get("symbol") or "your research question",
            synthesis.executive_summary,
            "",
            drivers,
            synthesis.what_to_watch,
        )
        key = investigation_output_key(state["user_id"], state["investigation_id"], "audio", "brief.wav")
        duration = await narrate(ctx.ai, ctx.storage, script, key)
        return AgentOutput(
            {"audio_key": key, "audio_duration": duration},
            f"Generated a {int(duration // 60)}:{int(duration % 60):02d} audio briefing",
        )


def default_agents() -> dict[str, Agent]:
    agents: list[Agent] = [
        OrchestratorAgent(),
        MarketAgent(),
        NewsAgent(),
        FinancialAgent(),
        MacroAgent(),
        DocumentAgent(),
        VisionAgentProxy(),
        AudioAgent(),
        VideoAgent(),
        SentimentAgent(),
        EventDetectionAgent(),
        RiskAgent(),
        EvidenceAgent(),
        SynthesisAgent(),
        VoiceAgent(),
    ]
    return {a.name: a for a in agents}


class VisionAgentProxy:
    """Lazy import keeps Pillow out of module import time for the API process."""

    name = "vision"
    label = "Vision Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        from app.agents.vision import VisionAgent

        return await VisionAgent().run(state, ctx)


def _safe_failure(agent: str, exc: Exception) -> str:
    label = AGENT_LABELS.get(agent, agent)
    if isinstance(exc, AIUnavailableError):
        return f"{label} skipped: AI model not configured"
    return f"{label} could not complete ({type(exc).__name__})"


def build_investigation_graph(
    ctx: AgentContext, reporter: ProgressReporter, agents: dict[str, Agent] | None = None
) -> Any:
    registry = agents or default_agents()

    def make_node(name: str) -> Any:
        agent = registry[name]

        async def node(state: InvestigationState) -> dict[str, Any]:
            plan = state.get("plan")
            if name == "voice":
                if not state.get("generate_audio"):
                    return {}
            elif name != "orchestrator" and (plan is None or name not in plan.agents):
                return {}
            reporter.agent_started(name)
            started_at, t0 = utc_now_iso(), time.perf_counter()
            warnings: list[str] = []
            update: dict[str, Any] = {}
            try:
                out = await agent.run(dict(state), ctx)
                update, summary, outcome, warnings = dict(out.update), out.summary, "completed", out.warnings
            except InvestigationDeleted:
                raise
            except AgentSkipped as exc:
                summary, outcome = str(exc), "skipped"
            except Exception as exc:
                logger.exception("agent_failed", extra={"agent": name, "error_type": type(exc).__name__})
                summary, outcome = _safe_failure(name, exc), "failed"
                warnings = [summary]
            duration = int((time.perf_counter() - t0) * 1000)
            if name == "orchestrator" and "plan" in update:
                reporter.set_plan(update["plan"].agents, bool(state.get("generate_audio")))
            reporter.agent_finished(name, outcome, summary, duration)
            update["agent_runs"] = [
                AgentRun(
                    agent=name,
                    status=outcome,
                    summary=summary,
                    started_at=started_at,
                    finished_at=utc_now_iso(),
                    duration_ms=duration,
                )
            ]
            update["warnings"] = warnings
            return update

        return node

    graph = StateGraph(InvestigationState)
    for name in [
        "orchestrator",
        *COLLECTORS,
        "sentiment",
        "event_detection",
        "risk",
        "evidence",
        "synthesis",
        "voice",
    ]:
        graph.add_node(name, make_node(name))
    graph.add_node("collection_done", lambda state: {})

    def route_collectors(state: InvestigationState) -> list[str]:
        plan = state.get("plan")
        selected = [c for c in COLLECTORS if plan is not None and c in plan.agents]
        return selected or ["collection_done"]

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", route_collectors, [*COLLECTORS, "collection_done"])
    for collector in COLLECTORS:
        graph.add_edge(collector, "collection_done")
    graph.add_edge("collection_done", "sentiment")
    graph.add_edge("collection_done", "event_detection")
    graph.add_edge("sentiment", "risk")
    graph.add_edge("event_detection", "risk")
    graph.add_edge("risk", "evidence")
    graph.add_edge("evidence", "synthesis")
    graph.add_edge("synthesis", "voice")
    graph.add_edge("voice", END)
    return graph.compile()
