from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.agents.audio import AudioAgent
from app.agents.base import AgentSkipped
from app.agents.document import DocumentAgent
from app.agents.events import EventDetectionAgent
from app.agents.evidence import EvidenceAgent
from app.agents.financial import FinancialAgent
from app.agents.macro import MacroAgent
from app.agents.market import MarketAgent, benchmark_for
from app.agents.news import NewsAgent, entity_terms
from app.agents.orchestrator import OrchestratorAgent, enforce_constraints, rule_based_plan
from app.agents.risk import RiskAgent, rule_based_risks
from app.agents.sentiment import SentimentAgent
from app.agents.synthesis import SynthesisAgent, merge_claims
from app.agents.vision import VisionAgent
from app.container import Container
from app.integrations.storage.base import upload_key
from app.schemas.agents import AgentPlan
from app.schemas.investigations import AttachmentRef
from app.workflows.state import merge_sources
from tests.conftest import DEMO_DATA, make_container
from tests.fakes import FakeGateway


def base_state(**extra: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "investigation_id": "inv_t",
        "user_id": "u1",
        "symbol": "NVDA",
        "asset_name": "NVIDIA Corporation",
        "asset_type": "equity",
        "question": "Why did NVIDIA fall today?",
        "attachments": [],
        "plan": AgentPlan(intent="why_move", agents=["market", "news"], rationale="", time_window_days=7),
        "sources": [],
    }
    state.update(extra)
    return state


async def collect(c: Container, state: dict[str, Any], *agents: Any) -> dict[str, Any]:
    ctx = c.agent_context()
    for agent in agents:
        out = await agent.run(state, ctx)
        for key, value in out.update.items():
            state[key] = merge_sources(state.get("sources"), value) if key == "sources" else value
    return state


def test_entity_terms_and_benchmarks() -> None:
    assert entity_terms("NVDA", "NVIDIA Corporation", "equity") == ["NVIDIA", "NVDA"]
    assert entity_terms("BTC-USD", "Bitcoin", "crypto") == ["Bitcoin", "BTC"]
    assert entity_terms("^GSPC", "S&P 500", "index") == ["S&P 500"]
    assert benchmark_for("NVDA", "equity") == "^GSPC"
    assert benchmark_for("ETH-USD", "crypto") == "BTC-USD"
    assert benchmark_for("EURUSD=X", "fx") is None


def test_orchestrator_rules_enforce_minimum_team_and_constraints() -> None:
    plan = enforce_constraints(
        AgentPlan(intent="why_move", agents=["market"], rationale="", time_window_days=7),
        "equity",
        True,
        set(),
    )
    assert {"news", "financial", "sentiment", "risk", "evidence", "synthesis"} <= set(plan.agents)
    crypto = rule_based_plan("Why did bitcoin fall?", "crypto", True, set())
    assert "financial" not in crypto.agents
    call = rule_based_plan("Summarize this earnings call", None, False, {"audio"})
    assert call.intent == "earnings_review" and "audio" in call.agents and "market" not in call.agents
    chart = rule_based_plan("Analyze this chart", "equity", True, {"image"})
    assert chart.intent == "chart_review" and "vision" in chart.agents and "news" not in chart.agents
    no_file = enforce_constraints(
        AgentPlan(intent="document_review", agents=["document"], rationale="", time_window_days=7),
        "equity",
        True,
        set(),
    )
    assert "document" not in no_file.agents


async def test_orchestrator_llm_plan_is_constrained(container: Container) -> None:
    out = await OrchestratorAgent().run(base_state(), container.agent_context())
    plan = out.update["plan"]
    assert plan.intent == "why_move" and "risk" in plan.agents  # LLM proposed only market+news


async def test_orchestrator_falls_back_without_ai(tmp_path: Path) -> None:
    c = make_container(tmp_path, ai=FakeGateway(roles=set()))
    out = await OrchestratorAgent().run(base_state(), c.agent_context())
    assert out.update["plan"].rationale == "Rule-based plan."


async def test_market_news_sentiment_events_evidence_pipeline(container: Container) -> None:
    state = await collect(
        container,
        base_state(),
        MarketAgent(),
        NewsAgent(),
        FinancialAgent(),
        SentimentAgent(),
        EventDetectionAgent(),
        EvidenceAgent(),
    )
    m = state["market"].metrics
    assert m.move_pct == pytest.approx(-6.2, abs=0.01) and m.unusual_move
    assert state["market"].intraday and m.benchmark_symbol == "^GSPC"
    news = state["news"]
    assert news.articles_reviewed == 9
    assert all(c.theme != "Theme 2" for c in news.clusters)  # off-topic cluster filtered by LLM relevance
    assert news.clusters[0].theme == "Export restrictions" and news.clusters[0].source_count == 5
    sentiment = state["sentiment"]
    assert sentiment.label == "negative" and sentiment.evidence_confidence in ("high", "medium")
    assert sentiment.timeline
    events = state["events"].events
    assert (
        any(e.origin == "news" for e in events)
        and any(e.origin == "market" for e in events)
        and any(e.origin == "filing" for e in events)
    )
    evidence = state["evidence"]
    assert evidence.drivers[0].name == "Export restrictions"
    assert sum(d.contribution_score for d in evidence.drivers) == pytest.approx(100.0)
    known = {s.id for s in state["sources"]}
    assert all(e in known for d in evidence.drivers for e in d.evidence_ids)
    assert any(c.claim_type == "observed_fact" for c in evidence.claims)


async def test_risk_agent_drops_unsupported_risks(container: Container) -> None:
    state = await collect(container, base_state(), MarketAgent(), NewsAgent())
    out = await RiskAgent().run(state, container.agent_context())
    items = out.update["risks"].items
    assert [i.risk for i in items] == ["regulatory"]  # 'valuation' cited only an invented id
    assert "made_up_id" not in items[0].evidence_ids
    assert all(e in {s.id for s in state["sources"]} for e in items[0].evidence_ids)


async def test_rule_based_risks_without_ai(container: Container) -> None:
    state = await collect(container, base_state(), MarketAgent(), NewsAgent())
    risks = rule_based_risks(state)
    assert risks[0].risk == "market"
    assert any(r.risk == "regulatory" for r in risks)


async def test_synthesis_guardrails_and_claim_validation(container: Container) -> None:
    state = await collect(container, base_state(), MarketAgent(), NewsAgent(), EvidenceAgent())
    out = await SynthesisAgent().run(state, container.agent_context())
    syn = out.update["synthesis"]
    assert "caused" not in syn.executive_summary and "likely drove" in syn.executive_summary
    assert "buy" not in syn.executive_summary.lower()
    claims = merge_claims(state["evidence"].claims, syn, state)
    texts = {c.claim: c for c in claims}
    assert "Fabricated fact with no evidence." not in texts
    assert texts["Interpretation without evidence."].claim_type == "hypothesis"
    assert texts["Export news is the main reported concern."].evidence_ids


async def test_synthesis_without_ai_is_deterministic(tmp_path: Path) -> None:
    c = make_container(tmp_path, ai=FakeGateway(roles=set()))
    state = await collect(c, base_state(), MarketAgent(), EvidenceAgent())
    out = await SynthesisAgent().run(state, c.agent_context())
    assert out.update["ai_narrative_available"] is False
    assert "fell" in out.update["synthesis"].executive_summary


async def test_macro_agent(container: Container) -> None:
    out = await MacroAgent().run(base_state(), container.agent_context())
    assert out.update["macro"].indicators
    assert any("FRED" in n for n in out.update["macro"].notes)


def _attach(c: Container, kind: str, filename: str, mime: str) -> AttachmentRef:
    data = (DEMO_DATA / filename).read_bytes() if (DEMO_DATA / filename).exists() else _synthetic(kind)
    key = upload_key("u1", kind, f"up_{kind}", filename)
    c.storage.put_bytes(key, data, mime)
    return AttachmentRef(
        upload_id=f"up_{kind}",
        kind=kind,
        filename=filename,
        content_type=mime,
        storage_key=key,
        size_bytes=len(data),
    )  # type: ignore[arg-type]


def _synthetic(kind: str) -> bytes:
    import io

    from PIL import Image

    if kind == "image":
        buf = io.BytesIO()
        Image.new("RGB", (64, 32), (10, 10, 10)).save(buf, format="PNG")
        return buf.getvalue()
    if kind == "audio":
        from app.integrations.ai.audio_utils import pcm16_to_wav

        return pcm16_to_wav(b"\x00\x00" * 2400)
    import sys

    sys.path.insert(0, str(DEMO_DATA.parent / "scripts"))
    from generate_demo_assets import earnings_release_pdf  # type: ignore[import-not-found]

    return bytes(earnings_release_pdf())


async def test_document_agent_text_then_vision(container: Container) -> None:
    att = _attach(container, "document", "northwind_q3_fy2026_results.pdf", "application/pdf")
    out = await DocumentAgent().run(base_state(attachments=[att]), container.agent_context())
    doc = out.update["documents"][0]
    assert doc.page_count == 2 and doc.key_facts[0].value == "$4.2 billion"
    assert doc.visual_pages and doc.visual_pages[0].page == 2  # table-heavy page sent to vision
    assert set(doc.pages_analyzed) == {1, 2}
    assert out.update["sources"][0].source_type == "document"


async def test_vision_and_audio_agents(container: Container) -> None:
    img = _attach(container, "image", "nvda_chart.png", "image/png")
    wav = _attach(container, "audio", "earnings_call.wav", "audio/wav")
    state = base_state(attachments=[img, wav])
    v = await VisionAgent().run(state, container.agent_context())
    assert v.update["images"][0].image_type == "price_chart"
    a = await AudioAgent().run(state, container.agent_context())
    clip = a.update["audio"][0]
    assert clip.segment_count == 2 and clip.transcript_key and container.storage.size(clip.transcript_key)
    assert clip.analysis is not None
    assert clip.analysis.notable_quotes == ["Revenue grew 31 percent"]  # invented quote removed


async def test_agents_skip_without_inputs(container: Container) -> None:
    ctx = container.agent_context()
    for agent in (DocumentAgent(), VisionAgent(), AudioAgent()):
        with pytest.raises(AgentSkipped):
            await agent.run(base_state(), ctx)
    with pytest.raises(AgentSkipped):
        await MarketAgent().run(base_state(symbol=None), ctx)
