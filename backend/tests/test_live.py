"""Live tests against real services (OpenRouter models, Yahoo Finance, SEC EDGAR, GDELT/Yahoo news).

Skipped by default. Run them explicitly (costs a few cents of OpenRouter credit):

    RUN_LIVE_TESTS=1 pytest -m live -v           # macOS/Linux
    $env:RUN_LIVE_TESTS=1; pytest -m live -v      # PowerShell

They read OPENROUTER_API_KEY (or OPEN_ROUTER_API_KEY) from the repo `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.container import Container
from app.schemas.agents import AgentPlan, Transcript
from app.schemas.investigations import AttachmentRef, InvestigationRecord
from app.utils.time import utc_now_iso
from app.workflows.investigation_runner import run_investigation
from tests.conftest import DEMO_DATA, REPO_ROOT

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to run live tests"
    ),
]


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@pytest.fixture
def live(tmp_path: Path) -> Container:
    env = read_dotenv(REPO_ROOT / ".env")
    key = (
        env.get("OPENROUTER_API_KEY")
        or env.get("OPEN_ROUTER_API_KEY")
        or os.environ.get("LIVE_OPENROUTER_API_KEY")
    )
    if not key:
        pytest.skip("No OpenRouter key in .env")
    settings = Settings(_env_file=None, local_data_dir=tmp_path, openrouter_api_key=key, gdelt_enabled=True)  # type: ignore[call-arg]
    return Container(settings)


async def test_live_reasoning_structured_output(live: Container) -> None:
    plan = await live.ai.structured(
        AgentPlan,
        system="Plan which agents to run. Reply with JSON only.",
        user='{"question": "Why did NVIDIA fall today?", "asset": "NVDA"}',
        agent="orchestrator",
        purpose="live_test",
    )
    assert plan.agents and live.ai.tracker.records[-1].model.startswith("openai/")


async def test_live_market_and_sec(live: Container) -> None:
    history = await live.market.get_history("NVDA", "6mo")
    assert len(history) > 100 and history[-1].close > 0
    assert live.financial is not None
    snap = await live.financial.snapshot("NVDA")
    assert snap.cik == "0001045810" and snap.revenue and snap.revenue > 1e9


async def test_live_news(live: Container) -> None:
    from app.integrations.news.base import NewsQuery

    result = await live.news.search_all(NewsQuery(terms=["NVIDIA", "NVDA"], symbol="NVDA", days=7))
    assert result.providers_used and result.articles


async def test_live_transcription_of_demo_call(live: Container) -> None:
    from app.integrations.ai.base import AudioInput
    from app.prompts.loader import system_prompt

    wav = DEMO_DATA / "earnings_call.wav"
    if not wav.exists():
        pytest.skip("Run scripts/generate_demo_audio.py first")
    transcript = await live.ai.structured(
        Transcript,
        system=system_prompt("transcription"),
        user="Transcribe this recording.",
        audio=[AudioInput(wav.read_bytes(), "audio/wav")],
        role="transcription",
        agent="audio",
        purpose="live_transcription",
        max_tokens=12000,
    )
    text = " ".join(s.text for s in transcript.segments).lower()
    assert "northwind" in text and len({s.speaker for s in transcript.segments}) >= 3


async def test_live_tts(live: Container) -> None:
    out = await live.ai.speech("SignalRoom live test. Markets were calm today.")
    assert out.wav[:4] == b"RIFF" and out.duration_seconds > 1


async def test_live_full_investigation_with_chart(live: Container) -> None:
    chart = DEMO_DATA / "nvda_chart.png"
    attachments = []
    if chart.exists():
        key = "users/u_live/uploads/images/up_live/nvda_chart.png"
        live.storage.put_bytes(key, chart.read_bytes(), "image/png")
        attachments.append(
            AttachmentRef(
                upload_id="up_live",
                kind="image",
                filename="nvda_chart.png",
                content_type="image/png",
                storage_key=key,
            )
        )
    now = utc_now_iso()
    live.repos.investigations.put(
        InvestigationRecord(
            investigation_id="inv_live",
            user_id="u_live",
            symbol="NVDA",
            asset_name="NVIDIA Corporation",
            asset_type="equity",
            question="Why did NVIDIA move today?",
            attachments=attachments,
            created_at=now,
            updated_at=now,
        )
    )
    await run_investigation(live, "inv_live")
    record = live.repos.investigations.get("inv_live")
    assert record is not None and record.status == "completed", record.error if record else None
    result = record.result
    assert result is not None and result.ai_narrative_available and result.executive_summary
    assert result.market is not None and result.drivers
    assert {r.agent for r in result.agent_runs if r.status == "completed"} >= {
        "orchestrator",
        "market",
        "synthesis",
        "evidence",
    }
    print(f"\nLive investigation cost: ${sum(u.cost_usd or 0 for u in result.model_usage):.4f}")


async def test_live_video_investigation_and_semantic_search(live: Container) -> None:
    video = DEMO_DATA / "northwind_webinar.mp4"
    chart = DEMO_DATA / "nvda_chart.png"
    if not video.exists():
        pytest.skip("Run scripts/generate_demo_video.py first")
    attachments = []
    for upload_id, path, kind, mime in (
        ("up_vid", video, "video", "video/mp4"),
        ("up_img", chart, "image", "image/png"),
    ):
        if path.exists():
            key = f"users/u_live/uploads/{kind}s/{upload_id}/{path.name}"
            live.storage.put_bytes(key, path.read_bytes(), mime)
            attachments.append(
                AttachmentRef(
                    upload_id=upload_id, kind=kind, filename=path.name, content_type=mime, storage_key=key
                )
            )  # type: ignore[arg-type]
    now = utc_now_iso()
    live.repos.investigations.put(
        InvestigationRecord(
            investigation_id="inv_live_video",
            user_id="u_live",
            question="Summarize this results webinar: key figures, guidance and risks.",
            attachments=attachments,
            created_at=now,
            updated_at=now,
        )
    )
    await run_investigation(live, "inv_live_video")
    record = live.repos.investigations.get("inv_live_video")
    assert record is not None and record.status == "completed", record.error if record else None
    assert record.result is not None and record.result.videos
    vid = record.result.videos[0]
    assert vid.segment_count >= 3 and vid.slides, vid
    print(f"\nVideo: {vid.segment_count} segments, {len(vid.slides)} slides, tone={vid.management_tone}")
    for s in vid.slides[:4]:
        print(f"  [{s.timestamp}] {s.title}: {[(f.fact, f.value) for f in s.figures[:3]]}")

    search = live.search_index()
    res = await search.search("u_live", "what did they say about guidance for next year?")
    assert res.mode == "semantic" and res.hits
    print(
        f"Search hits: {[(h.modality, h.location, round(h.score, 2), h.snippet[:60]) for h in res.hits[:4]]}"
    )
    if chart.exists():
        by_image = await search.search_by_image("u_live", chart.read_bytes(), "image/png")
        assert by_image.hits[0].modality == "image"
        print(f"Image query top hit: {by_image.hits[0].title} ({by_image.hits[0].score})")
    print(f"Cost: ${sum(u.cost_usd or 0 for u in record.result.model_usage):.4f}")
