from __future__ import annotations

from pathlib import Path

from app.container import Container
from app.schemas.investigations import FollowUp, InvestigationRecord
from app.utils.time import utc_now_iso
from app.workflows.followup import plan_followup, run_followup
from app.workflows.investigation_runner import failure_message, run_investigation
from app.workflows.media import infographic_prompt, run_infographic, run_investigation_audio
from tests.conftest import make_container
from tests.fakes import FakeGateway, FakeMarket


def new_record(c: Container, **extra: object) -> InvestigationRecord:
    now = utc_now_iso()
    data: dict[str, object] = {
        "investigation_id": "inv_1",
        "user_id": "u1",
        "symbol": "NVDA",
        "asset_name": "NVIDIA Corporation",
        "asset_type": "equity",
        "question": "Why did NVIDIA fall today?",
        "created_at": now,
        "updated_at": now,
    }
    data.update(extra)
    record = InvestigationRecord.model_validate(data)
    c.repos.investigations.put(record)
    return record


async def test_full_investigation_graph(container: Container) -> None:
    new_record(container, generate_audio=True, audio_status="pending")
    await run_investigation(container, "inv_1")
    r = container.repos.investigations.get("inv_1")
    assert r is not None and r.status == "completed" and r.progress == 100
    res = r.result
    assert res is not None
    ran = {a.agent: a.status for a in res.agent_runs}
    assert ran["orchestrator"] == "completed"
    for agent in (
        "market",
        "news",
        "financial",
        "macro",
        "sentiment",
        "event_detection",
        "risk",
        "evidence",
        "synthesis",
        "voice",
    ):
        assert ran.get(agent) == "completed", (agent, ran)
    assert res.drivers and abs(sum(d.contribution_score for d in res.drivers) - 100) < 0.01
    assert res.risks and res.risks.items
    assert r.audio_status == "ready" and r.audio_key and container.storage.size(r.audio_key)
    assert res.model_usage and all(u.provider == "fake" for u in res.model_usage)
    assert res.sources[0].id in {e for d in res.drivers for e in d.evidence_ids} | {
        e for c in res.claims for e in c.evidence_ids
    }

    events = container.repos.events.list_after("inv_1")
    types = [e.event_type for e in events]
    assert types[0] == "running" and types[-1] == "completed"
    progress = [e.progress for e in events if e.progress is not None]
    assert progress == sorted(progress)  # never goes backwards
    statuses = [e.status for e in events]
    for expected in ("collecting_data", "analyzing", "synthesizing", "generating_audio", "completed"):
        assert expected in statuses
    seqs = [e.seq for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


async def test_investigation_is_idempotent(container: Container) -> None:
    new_record(container)
    await run_investigation(container, "inv_1")
    calls = len(container.ai.calls)  # type: ignore[attr-defined]
    await run_investigation(container, "inv_1")  # SQS redelivery
    assert len(container.ai.calls) == calls  # type: ignore[attr-defined]


async def test_degrades_without_ai(tmp_path: Path) -> None:
    c = make_container(tmp_path, ai=FakeGateway(roles=set()))
    new_record(c)
    await run_investigation(c, "inv_1")
    r = c.repos.investigations.get("inv_1")
    assert r is not None and r.status == "completed" and r.result is not None
    assert r.result.ai_narrative_available is False
    assert r.result.drivers  # deterministic scores still available


async def test_news_outage_degrades_gracefully(tmp_path: Path) -> None:
    c = make_container(tmp_path, news_fail=True)
    new_record(c)
    await run_investigation(c, "inv_1")
    r = c.repos.investigations.get("inv_1")
    assert r is not None and r.status == "completed" and r.result is not None
    assert {a.agent: a.status for a in r.result.agent_runs}["news"] == "failed"
    assert any("News Agent" in w for w in r.result.warnings)
    assert r.result.market is not None  # the rest of the investigation continued


async def test_fails_safely_when_no_data(tmp_path: Path) -> None:
    c = make_container(tmp_path, market=FakeMarket(fail={"*"}), news_fail=True)
    new_record(c)
    await run_investigation(c, "inv_1")
    r = c.repos.investigations.get("inv_1")
    assert r is not None and r.status == "failed"
    assert r.error and "Traceback" not in r.error and "retry" in r.error
    assert c.repos.events.list_after("inv_1")[-1].event_type == "failed"


def test_failure_message_wording() -> None:
    from app.schemas.agents import AgentRun

    runs = [
        AgentRun(
            agent="market", status="completed", summary="", started_at="", finished_at="", duration_ms=1
        ),
        AgentRun(agent="news", status="failed", summary="", started_at="", finished_at="", duration_ms=1),
    ]
    assert failure_message({"agent_runs": runs}) == (
        "Could not complete the investigation. Market data was available, but the news provider was unavailable. You can retry."
    )


async def test_deleted_during_run_stops_quietly(container: Container) -> None:
    new_record(container)
    original = container.repos.investigations.get

    calls = {"n": 0}

    def flaky_get(investigation_id: str):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return original(investigation_id) if calls["n"] < 4 else None

    container.repos.investigations.get = flaky_get  # type: ignore[method-assign]
    await run_investigation(container, "inv_1")  # must not raise


async def test_followup_minimal_work_and_media(container: Container) -> None:
    new_record(container)
    await run_investigation(container, "inv_1")
    r = container.repos.investigations.get("inv_1")
    assert r is not None
    r.followups.append(
        FollowUp(
            followup_id="fu_1", question="What would invalidate this explanation?", created_at=utc_now_iso()
        )
    )
    container.repos.investigations.put(r)
    before = list(container.ai.calls)  # type: ignore[attr-defined]
    await run_followup(container, "inv_1", "fu_1")
    new_calls = container.ai.calls[len(before) :]  # type: ignore[attr-defined]
    assert new_calls == ["embedding_text", "followup_answer"]  # retrieval query only; no agents re-run
    fu = container.repos.investigations.get("inv_1").followups[0]  # type: ignore[union-attr]
    assert fu.status == "completed" and fu.answer and "invented" not in fu.evidence_ids

    await run_investigation_audio(container, "inv_1")
    await run_infographic(container, "inv_1")
    r = container.repos.investigations.get("inv_1")
    assert r is not None and r.audio_status == "ready" and r.infographic_status == "ready"
    calls = len(container.ai.calls)  # type: ignore[attr-defined]
    await run_investigation_audio(container, "inv_1")  # unchanged → not regenerated
    assert len(container.ai.calls) == calls  # type: ignore[attr-defined]
    assert "Evidence-weighted" in infographic_prompt(r)


def test_plan_followup_rules() -> None:
    state = {"symbol": "NVDA", "asset_type": "equity", "financial": None, "news": object()}
    assert plan_followup("Compare with the last earnings report", state, set()) == ["financial"]
    assert plan_followup("Does this change the thesis?", state, {"audio"}) == ["audio"]
    assert plan_followup("What is the latest news?", state, set()) == []  # news already present
