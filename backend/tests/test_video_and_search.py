"""Video Agent (speech + slides) and multimodal semantic search."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.agents.base import AgentSkipped
from app.agents.orchestrator import enforce_constraints, rule_based_plan
from app.agents.video import VideoAgent
from app.container import Container
from app.schemas.agents import AgentPlan
from app.services.search_index import cosine, lexical_score
from tests.conftest import DEMO_DATA, signup
from tests.fakes import FakeGateway
from tests.test_agents import _attach, base_state
from tests.test_api_flows import drain, png_bytes, upload

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


async def test_video_agent_reads_speech_and_slides(container: Container) -> None:
    clip = _attach(container, "video", "northwind_webinar.mp4", "video/mp4")
    out = await VideoAgent().run(base_state(attachments=[clip]), container.agent_context())
    vid = out.update["videos"][0]
    assert vid.segment_count == 2 and vid.slides[0].figures[0].value == "$4.2B"
    assert vid.management_tone == "confident" and vid.guidance
    assert vid.notable_quotes == [
        "Revenue grew 18 percent to 4.2 billion dollars this quarter."
    ]  # invented quote dropped
    assert vid.transcript_key and container.storage.size(vid.transcript_key)
    assert out.update["sources"][0].source_type == "video"


async def test_video_agent_skips_and_requires_model(container: Container) -> None:
    with pytest.raises(AgentSkipped):
        await VideoAgent().run(base_state(), container.agent_context())
    clip = _attach(container, "video", "northwind_webinar.mp4", "video/mp4")
    container.__dict__["ai"] = FakeGateway(roles={"reasoning"})
    from app.integrations.ai.base import AIUnavailableError

    with pytest.raises(AIUnavailableError):
        await VideoAgent().run(base_state(attachments=[clip]), container.agent_context())


def test_orchestrator_plans_video_agent() -> None:
    plan = rule_based_plan("What did management say?", "equity", True, {"video"})
    assert plan.intent == "earnings_review" and "video" in plan.agents and "sentiment" in plan.agents
    no_video = enforce_constraints(
        AgentPlan(intent="why_move", agents=["video", "market"], rationale="", time_window_days=7),
        "equity",
        True,
        set(),
    )
    assert "video" not in no_video.agents  # never runs without a file


def test_video_upload_validation(client: TestClient, auth: dict[str, str]) -> None:
    assert (
        client.post(
            "/api/v1/uploads/presign",
            json={"filename": "w.avi", "content_type": "video/x-msvideo", "size_bytes": 10, "kind": "video"},
            headers=auth,
        ).status_code
        == 422
    )
    pre = client.post(
        "/api/v1/uploads/presign",
        json={"filename": "w.mp4", "content_type": "video/mp4", "size_bytes": 20, "kind": "video"},
        headers=auth,
    ).json()
    client.put(
        pre["upload_url"].replace("http://localhost:8000", ""),
        content=b"definitely not an mp4",
        headers=pre["headers"],
    )
    bad = client.post("/api/v1/uploads/complete", json={"upload_id": pre["upload_id"]}, headers=auth)
    assert bad.status_code == 422
    assert upload(client, auth, "ok.mp4", "video/mp4", MP4, "video")


def _run(
    client: TestClient, auth: dict[str, str], container: Container, body: dict[str, object]
) -> dict[str, object]:
    resp = client.post("/api/v1/investigations", json=body, headers=auth)
    assert resp.status_code == 202, resp.text
    drain(container)
    view: dict[str, object] = client.get(
        f"/api/v1/investigations/{resp.json()['investigation_id']}", headers=auth
    ).json()
    assert view["status"] == "completed", view["error"]
    return view


def test_video_investigation_end_to_end_and_search(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    video_bytes = (DEMO_DATA / "northwind_webinar.mp4").read_bytes()
    vid_id = upload(client, auth, "webinar.mp4", "video/mp4", video_bytes, "video")
    chart = png_bytes()
    img_id = upload(client, auth, "chart.png", "image/png", chart, "image")
    view = _run(
        client,
        auth,
        container,
        {"question": "Summarize this webinar and its guidance.", "upload_ids": [vid_id, img_id]},
    )
    res = view["result"]
    assert isinstance(res, dict)
    assert res["videos"] and res["videos"][0]["slides"]
    assert any(d["driver_id"].startswith("drv_video_") for d in res["drivers"])
    assert any(u["purpose"] == "embedding_text" for u in res["model_usage"])  # indexing cost is tracked
    inv_id = view["investigation_id"]
    transcript = client.get(f"/api/v1/investigations/{inv_id}/transcripts/{vid_id}", headers=auth)
    assert transcript.status_code == 200 and len(transcript.json()["segments"]) == 2

    # semantic search finds the CFO's sentence in the video transcript
    found = client.get("/api/v1/search", params={"q": "logistics costs gross margin"}, headers=auth).json()
    assert found["mode"] == "semantic" and found["indexed_investigations"] == 1
    top = found["hits"][0]
    assert top["investigation_id"] == inv_id and top["modality"] == "video"
    video_only = client.get(
        "/api/v1/search", params={"q": "revenue", "modality": "video"}, headers=auth
    ).json()
    assert video_only["hits"] and all(h["modality"] == "video" for h in video_only["hits"])

    # image query: the same chart is found natively
    by_image = client.post(
        "/api/v1/search/by-image", files={"file": ("q.png", chart, "image/png")}, headers=auth
    ).json()
    assert by_image["mode"] == "image" and by_image["hits"][0]["modality"] == "image"
    assert by_image["hits"][0]["ref"] == img_id
    bad = client.post(
        "/api/v1/search/by-image", files={"file": ("q.txt", b"hello", "text/plain")}, headers=auth
    )
    assert bad.status_code == 422

    # follow-ups receive the retrieved passages
    container.ai.calls.clear()  # type: ignore[attr-defined]
    fu = client.post(
        f"/api/v1/investigations/{inv_id}/followups",
        json={"question": "What did the CFO say about margins?"},
        headers=auth,
    )
    assert fu.status_code == 202
    drain(container)
    assert "embedding_text" in container.ai.calls  # type: ignore[attr-defined]

    # other users cannot see the index; deleting removes it
    eve = signup(client, "eve@example.com")
    assert client.get("/api/v1/search", params={"q": "logistics"}, headers=eve).json()["hits"] == []
    assert client.delete(f"/api/v1/investigations/{inv_id}", headers=auth).status_code in (200, 204)
    assert (
        client.get("/api/v1/search", params={"q": "logistics"}, headers=auth).json()["indexed_investigations"]
        == 0
    )


def test_search_keyword_fallback_without_embeddings(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    container.__dict__["ai"] = FakeGateway(roles={"reasoning", "vision", "transcription"})
    img_id = upload(client, auth, "q.png", "image/png", png_bytes(), "image")
    _run(
        client,
        auth,
        container,
        {"asset": "NVDA", "question": "Why did NVIDIA move today?", "upload_ids": [img_id]},
    )
    res = client.get("/api/v1/search", params={"q": "export restrictions"}, headers=auth).json()
    assert res["mode"] == "keyword" and res["hits"]
    assert (
        client.post(
            "/api/v1/search/by-image", files={"file": ("q.png", png_bytes(), "image/png")}, headers=auth
        ).status_code
        == 503
    )
    assert client.get("/api/v1/search", params={"q": "x"}, headers=auth).status_code == 422


def test_scoring_helpers() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0 and cosine([1.0], [1.0, 2.0]) == 0.0
    from app.services.search_index import _tokens

    assert lexical_score(_tokens("gross margin"), "Gross margins compressed") == 1.0
    assert lexical_score(_tokens("the of"), "anything") == 0.0
    buf = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buf, format="PNG")
    assert buf.getvalue().startswith(b"\x89PNG")
