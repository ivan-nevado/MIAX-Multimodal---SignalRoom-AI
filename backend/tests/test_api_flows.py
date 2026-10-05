"""End-to-end API flows with the in-process queue: HTTP → queue → worker → HTTP."""

from __future__ import annotations

import asyncio
import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from app.container import Container
from app.integrations.ai.audio_utils import pcm16_to_wav
from app.workers.sqs_worker import Worker


def drain(container: Container, queue: str = "investigations") -> None:
    async def run() -> None:
        worker = Worker(container, wait_seconds=0)
        while await worker.process_one(queue):  # type: ignore[arg-type]
            pass

    asyncio.run(run())


def upload(client: TestClient, auth: dict[str, str], filename: str, mime: str, data: bytes, kind: str) -> str:
    pre = client.post(
        "/api/v1/uploads/presign",
        json={"filename": filename, "content_type": mime, "size_bytes": len(data), "kind": kind},
        headers=auth,
    )
    assert pre.status_code == 200, pre.text
    body = pre.json()
    put = client.put(
        body["upload_url"].replace("http://localhost:8000", ""), content=data, headers=body["headers"]
    )
    assert put.status_code == 200, put.text
    done = client.post("/api/v1/uploads/complete", json={"upload_id": body["upload_id"]}, headers=auth)
    assert done.status_code == 200, done.text
    return str(body["upload_id"])


def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (1, 2, 3)).save(buf, format="PNG")
    return buf.getvalue()


def test_health_and_openapi(client: TestClient) -> None:
    health = client.get("/api/v1/health").json()
    assert health["status"] == "ok" and health["checks"]["database"] == "ok"
    assert health["providers"]["alpha_vantage"] is False  # optional key missing ≠ unhealthy
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    spec = client.get("/api/openapi.json").json()
    assert (
        "/api/v1/investigations" in spec["paths"]
        and "/api/v1/investigations/{investigation_id}/events" in spec["paths"]
    )
    resp = client.get("/api/v1/health/live")
    assert resp.headers["X-Content-Type-Options"] == "nosniff" and resp.headers["X-Request-ID"]


def test_watchlist_crud_reorder_and_limits(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    items = client.get("/api/v1/watchlist", headers=auth).json()
    assert [i["symbol"] for i in items] == [
        "NVDA",
        "TSLA",
        "BTC-USD",
        "^GSPC",
        "EURUSD=X",
    ]  # seeded demo watchlist
    assert items[0]["quote"]["last_price"] is not None
    added = client.post("/api/v1/watchlist", json={"symbol": "apple"}, headers=auth)
    assert added.status_code == 201 and added.json()["symbol"] == "AAPL"  # entity resolution
    assert client.post("/api/v1/watchlist", json={"symbol": "AAPL"}, headers=auth).status_code == 409
    assert client.post("/api/v1/watchlist", json={"symbol": "ZZZZ zz"}, headers=auth).status_code == 404
    order = ["AAPL", "NVDA", "TSLA", "BTC-USD", "^GSPC", "EURUSD=X"]
    assert client.put("/api/v1/watchlist/order", json={"symbols": order}, headers=auth).status_code == 204
    assert [i["symbol"] for i in client.get("/api/v1/watchlist", headers=auth).json()] == order
    assert client.put("/api/v1/watchlist/order", json={"symbols": ["NVDA"]}, headers=auth).status_code == 422
    assert client.delete("/api/v1/watchlist/%5EGSPC", headers=auth).status_code == 204
    assert client.delete("/api/v1/watchlist/%5EGSPC", headers=auth).status_code == 404
    container.settings.watchlist_max_size = 5
    resp = client.post("/api/v1/watchlist", json={"symbol": "MSFT"}, headers=auth)
    assert resp.status_code == 422 and "up to 5" in resp.json()["message"]


def test_assets_search_detail_and_overview(client: TestClient, auth: dict[str, str]) -> None:
    results = client.get("/api/v1/assets/search?q=bitcoin", headers=auth).json()
    assert results[0]["symbol"] == "BTC-USD" and results[0]["source"] == "alias"
    detail = client.get("/api/v1/assets/NVIDIA?range=1mo", headers=auth).json()
    assert detail["quote"]["symbol"] == "NVDA" and detail["metrics"]["unusual_move"] is True
    assert detail["quote"]["delayed_notice"].startswith("Market data may be delayed")
    assert detail["news"] and detail["news"][0]["url"].startswith("https://")
    overview = client.get("/api/v1/market/overview", headers=auth).json()
    assert len(overview["indices"]) >= 5
    assert client.get("/api/v1/assets/NVDA?range=10y", headers=auth).status_code == 422


def test_investigation_lifecycle_with_sse(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    resp = client.post(
        "/api/v1/investigations",
        json={"asset": "NVIDIA", "question": "Why did NVIDIA fall today?", "generate_audio": True},
        headers=auth,
    )
    assert resp.status_code == 202 and resp.json()["status"] == "queued"
    inv = resp.json()["investigation_id"]
    queued = client.get(f"/api/v1/investigations/{inv}", headers=auth).json()
    assert queued["status"] == "queued" and queued["symbol"] == "NVDA"

    drain(container)
    view = client.get(f"/api/v1/investigations/{inv}", headers=auth).json()
    assert view["status"] == "completed" and view["progress"] == 100
    assert view["result"]["drivers"] and view["audio_status"] == "ready" and view["audio_url"]
    assert "storage_key" not in json.dumps(view["attachments"])
    audio = client.get(view["audio_url"].replace("http://localhost:8000", ""))
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"

    with client.stream("GET", f"/api/v1/investigations/{inv}/events", headers=auth) as stream:
        text = "".join(stream.iter_text())
    assert "event: progress" in text and "event: end" in text and '"status": "completed"' in text
    events = client.get(f"/api/v1/investigations/{inv}/events?format=json", headers=auth).json()
    last_seq = events[2]["seq"]
    later = client.get(
        f"/api/v1/investigations/{inv}/events?format=json&after={last_seq}", headers=auth
    ).json()
    assert len(later) == len(events) - 3

    listing = client.get("/api/v1/investigations", headers=auth).json()
    assert listing[0]["investigation_id"] == inv and listing[0]["move_pct"] is not None

    fu = client.post(
        f"/api/v1/investigations/{inv}/followups",
        json={"question": "What would invalidate this?"},
        headers=auth,
    )
    assert fu.status_code == 202
    assert (
        client.post(
            f"/api/v1/investigations/{inv}/followups", json={"question": "Another one?"}, headers=auth
        ).status_code
        == 409
    )
    drain(container)
    view = client.get(f"/api/v1/investigations/{inv}", headers=auth).json()
    assert view["followups"][0]["status"] == "completed"

    assert (
        client.post(f"/api/v1/investigations/{inv}/infographic", headers=auth).json()["status"] == "pending"
    )
    drain(container)
    view = client.get(f"/api/v1/investigations/{inv}", headers=auth).json()
    assert view["infographic_status"] == "ready" and view["infographic_url"]

    assert client.post(f"/api/v1/investigations/{inv}/retry", headers=auth).status_code == 409
    assert client.delete(f"/api/v1/investigations/{inv}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/investigations/{inv}", headers=auth).status_code == 404


def test_multimodal_research_uploads(client: TestClient, auth: dict[str, str], container: Container) -> None:
    import sys

    from tests.conftest import DEMO_DATA

    sys.path.insert(0, str(DEMO_DATA.parent / "scripts"))
    from generate_demo_assets import earnings_release_pdf  # type: ignore[import-not-found]

    pdf_id = upload(client, auth, "results.pdf", "application/pdf", earnings_release_pdf(), "document")
    img_id = upload(client, auth, "chart.png", "image/png", png_bytes(), "image")
    wav_id = upload(client, auth, "call.wav", "audio/wav", pcm16_to_wav(b"\x00\x00" * 4800), "audio")
    resp = client.post(
        "/api/v1/investigations",
        json={
            "question": "Summarize this earnings call and identify the most important risks.",
            "upload_ids": [pdf_id, img_id, wav_id],
        },
        headers=auth,
    )
    assert resp.status_code == 202, resp.text
    drain(container)
    view = client.get(f"/api/v1/investigations/{resp.json()['investigation_id']}", headers=auth).json()
    assert view["status"] == "completed", view["error"]
    res = view["result"]
    assert res["documents"] and res["images"] and res["audio"]
    assert view["plan"]["intent"] in ("earnings_review", "general_research", "why_move")
    transcript = client.get(
        f"/api/v1/investigations/{view['investigation_id']}/transcripts/{wav_id}", headers=auth
    )
    assert transcript.status_code == 200 and transcript.json()["segments"]


def test_upload_validation(client: TestClient, auth: dict[str, str]) -> None:
    def presign(**body: object) -> int:
        return client.post("/api/v1/uploads/presign", json=body, headers=auth).status_code

    assert presign(filename="x.exe", content_type="application/pdf", size_bytes=10, kind="document") == 422
    assert presign(filename="x.pdf", content_type="image/png", size_bytes=10, kind="document") == 422
    assert (
        presign(filename="x.pdf", content_type="application/pdf", size_bytes=999_999_999, kind="document")
        == 422
    )
    assert (
        presign(filename="../../etc/x.pdf", content_type="application/pdf", size_bytes=10, kind="document")
        == 200
    )  # path stripped
    pre = client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "fake.pdf",
            "content_type": "application/pdf",
            "size_bytes": 20,
            "kind": "document",
        },
        headers=auth,
    ).json()
    complete = client.post("/api/v1/uploads/complete", json={"upload_id": pre["upload_id"]}, headers=auth)
    assert complete.status_code == 422 and "not been uploaded" in complete.json()["message"]
    client.put(
        pre["upload_url"].replace("http://localhost:8000", ""),
        content=b"not really a pdf....",
        headers={"Content-Type": "application/pdf"},
    )
    complete = client.post("/api/v1/uploads/complete", json={"upload_id": pre["upload_id"]}, headers=auth)
    assert complete.status_code == 422 and "valid PDF" in complete.json()["message"]
    wrong_type = client.put(
        pre["upload_url"].replace("http://localhost:8000", ""),
        content=b"%PDF-1.4",
        headers={"Content-Type": "text/plain"},
    )
    assert wrong_type.status_code == 400


def test_investigation_validation(client: TestClient, auth: dict[str, str]) -> None:
    assert client.post("/api/v1/investigations", json={"question": "Hmm?"}, headers=auth).status_code == 422
    assert (
        client.post(
            "/api/v1/investigations", json={"asset": "ZZZZ zz", "question": "Why?"}, headers=auth
        ).status_code
        == 422
    )
    alias_in_text = client.post(
        "/api/v1/investigations", json={"question": "Why did Tesla rise this week?"}, headers=auth
    )
    assert alias_in_text.status_code == 202
    resp = client.post("/api/v1/investigations", json={"asset": "NVDA", "question": "x"}, headers=auth)
    assert resp.status_code == 422 and resp.json()["error"] == "validation_failed"


def test_briefings_preferences_and_email_preview(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    prefs = client.get("/api/v1/preferences/briefing", headers=auth).json()
    assert prefs == {
        "enabled": False,
        "local_time": "08:00",
        "timezone": "Europe/Madrid",
        "email_enabled": False,
        "audio_enabled": True,
        "voice": "professional",
    }
    assert (
        client.patch("/api/v1/preferences/briefing", json={"timezone": "Mars/Base"}, headers=auth).status_code
        == 422
    )
    assert (
        client.patch("/api/v1/preferences/briefing", json={"local_time": "25:00"}, headers=auth).status_code
        == 422
    )
    updated = client.patch(
        "/api/v1/preferences/briefing",
        json={"enabled": True, "local_time": "07:30", "email_enabled": True},
        headers=auth,
    ).json()
    assert updated["enabled"] and updated["local_time"] == "07:30"
    assert (
        client.patch("/api/v1/me/preferences", json={"timezone": "America/New_York"}, headers=auth).json()[
            "timezone"
        ]
        == "America/New_York"
    )

    gen = client.post(
        "/api/v1/briefings/generate", json={"with_audio": True, "send_email": True}, headers=auth
    )
    assert gen.status_code == 202
    bid = gen.json()["briefing_id"]
    assert client.post("/api/v1/briefings/generate", json={}, headers=auth).status_code == 409
    drain(container, "briefings")
    view = client.get(f"/api/v1/briefings/{bid}", headers=auth).json()
    assert (
        view["status"] == "completed"
        and view["headline"]
        and view["audio_status"] == "ready"
        and view["audio_url"]
    )
    assert view["email_status"] == "sent"
    assert all(sid != "fake_source" for s in view["sections"] for sid in s["source_ids"])
    html = client.get(f"/api/v1/briefings/{bid}/email-preview", headers=auth)
    assert html.status_code == 200 and "SignalRoom" in html.text and "unsubscribe" in html.text.lower()
    outbox = list((container.settings.local_data_dir / "outbox").glob("*.html"))
    assert len(outbox) == 1
    assert client.get("/api/v1/briefings", headers=auth).json()[0]["briefing_id"] == bid


def test_voice_command(client: TestClient, auth: dict[str, str]) -> None:
    wav = pcm16_to_wav(b"\x00\x00" * 1600)
    resp = client.post(
        "/api/v1/voice/transcribe", files={"file": ("cmd.wav", wav, "audio/wav")}, headers=auth
    )
    assert resp.status_code == 200 and resp.json()["resolved_symbol"] == "NVDA"
    bad = client.post(
        "/api/v1/voice/transcribe", files={"file": ("cmd.mp3", b"ID3xxxx", "audio/mpeg")}, headers=auth
    )
    assert bad.status_code == 422


def test_delete_my_data(client: TestClient, auth: dict[str, str], container: Container) -> None:
    client.post(
        "/api/v1/investigations", json={"asset": "NVDA", "question": "Why did it move?"}, headers=auth
    )
    drain(container)
    counts = client.delete("/api/v1/me/data", headers=auth).json()
    assert counts["investigations"] == 1
    assert client.get("/api/v1/investigations", headers=auth).json() == []


def test_rate_limit(client: TestClient, auth: dict[str, str], container: Container) -> None:
    from app.api.middleware import RateLimitMiddleware
    from app.main import create_app

    container.settings.rate_limit_per_minute = 3
    with TestClient(create_app()) as limited:
        codes = [limited.get("/api/v1/briefings", headers=auth).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[-1] == 429
    assert RateLimitMiddleware  # imported for clarity
