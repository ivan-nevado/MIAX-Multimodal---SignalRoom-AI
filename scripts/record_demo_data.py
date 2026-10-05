"""Record REAL SignalRoom runs into demo_data/ for the frontend demo mode (VITE_DEMO_MODE=true).

Demo mode replays genuine pipeline output (real market data, real headlines and source
links, real model output) recorded on a given date — nothing is invented. It runs:

  1. a "Why did NVIDIA move?" investigation with audio briefing + a follow-up + a visual brief
  2. a multimodal research investigation (synthetic earnings call audio + synthetic PDF)
  2b. a video research investigation (synthetic results webinar: speech + slides)
  3. a daily briefing for the demo watchlist (with audio and the rendered email)
  4. market snapshots for the demo watchlist and overview

Usage (repo root, needs OPENROUTER_API_KEY in .env; costs a few cents):
    backend/.venv/Scripts/python scripts/record_demo_data.py
    backend/.venv/Scripts/python scripts/record_demo_data.py --only video   # just step 2b
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
DEMO = ROOT / "demo_data"
PUBLIC = ROOT / "frontend" / "public" / "demo"

import os  # noqa: E402

os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp(prefix="signalroom-demo-"))

from app.config.logging import configure_logging  # noqa: E402
from app.container import get_container  # noqa: E402
from app.schemas.briefings import Briefing  # noqa: E402
from app.schemas.investigations import AttachmentRef, FollowUp, InvestigationRecord  # noqa: E402
from app.schemas.users import UserRecord  # noqa: E402
from app.services.asset_service import AssetService  # noqa: E402
from app.services.email_renderer import render_briefing_email  # noqa: E402
from app.services.watchlist_service import DEMO_WATCHLIST, WatchlistService  # noqa: E402
from app.utils.time import utc_now_iso  # noqa: E402
from app.workflows.briefing_flow import run_briefing  # noqa: E402
from app.workflows.followup import run_followup  # noqa: E402
from app.workflows.investigation_runner import run_investigation  # noqa: E402
from app.workflows.media import run_infographic  # noqa: E402

USER = "demo-user"


async def record_video(c: Any) -> None:
    print("2b/4 Video research (results webinar)…")
    fname = "northwind_webinar.mp4"
    raw = (DEMO / fname).read_bytes()
    key = f"users/{USER}/uploads/videos/up_demo_video/{fname}"
    c.storage.put_bytes(key, raw, "video/mp4")
    now = utc_now_iso()
    c.repos.investigations.put(InvestigationRecord(
        investigation_id="demo_webinar", user_id=USER,
        question="Summarize this results webinar: key figures shown on the slides, guidance and risks.",
        attachments=[AttachmentRef(upload_id="up_demo_video", kind="video", filename=fname, content_type="video/mp4", storage_key=key, size_bytes=len(raw))],
        created_at=now, updated_at=now,
    ))
    await run_investigation(c, "demo_webinar")
    rec = c.repos.investigations.get("demo_webinar")
    assert rec and rec.status == "completed", rec.error if rec else "missing"
    transcript = None
    if rec.result and rec.result.videos and rec.result.videos[0].transcript_key:
        transcript = json.loads(c.storage.get_bytes(rec.result.videos[0].transcript_key))
    dump("investigation_video.json", {
        "investigation": rec.model_dump(mode="json", exclude={"user_id", "audio_key", "infographic_key"}),
        "events": events_for(c, "demo_webinar"),
        "transcript": transcript,
    })


def downsample_wav(data: bytes, target_rate: int = 16000) -> bytes:
    """Shrink TTS audio for the static demo (24 kHz → 16 kHz mono)."""
    with wave.open(io.BytesIO(data)) as src:
        rate, frames = src.getframerate(), src.readframes(src.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    n_out = int(len(samples) * target_rate / rate)
    resampled = np.interp(np.linspace(0, len(samples) - 1, n_out), np.arange(len(samples)), samples).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(target_rate)
        out.writeframes(resampled.tobytes())
    return buf.getvalue()


def dump(name: str, data: Any) -> None:
    (DEMO / name).write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
    print(f"  wrote demo_data/{name}")


def events_for(c: Any, investigation_id: str) -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in c.repos.events.list_after(investigation_id)]


async def main() -> None:
    configure_logging("WARNING")
    c = get_container()
    if not c.ai.available("reasoning"):
        raise SystemExit("No AI provider configured (OPENROUTER_API_KEY).")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:] == ["--only", "video"]:
        await record_video(c)
        return
    c.repos.users.put(UserRecord(user_id=USER, email="demo@signalroom.ai", created_at=utc_now_iso()))
    assets = AssetService(c.market, c.news, c.repos.investigations, c.financial)
    WatchlistService(c.repos.watchlists, assets, 20).seed_demo(USER)

    print("1/4 NVIDIA investigation…")
    now = utc_now_iso()
    c.repos.investigations.put(InvestigationRecord(
        investigation_id="demo_nvda", user_id=USER, symbol="NVDA", asset_name="NVIDIA Corporation", asset_type="equity",
        question="Why did NVIDIA move today?", generate_audio=True, audio_status="pending", created_at=now, updated_at=now,
    ))
    await run_investigation(c, "demo_nvda")
    record = c.repos.investigations.get("demo_nvda")
    assert record and record.status == "completed", record.error if record else "missing"
    record.followups.append(FollowUp(followup_id="demo_fu", question="What would invalidate this explanation?", created_at=utc_now_iso()))
    c.repos.investigations.put(record)
    await run_followup(c, "demo_nvda", "demo_fu")
    await run_infographic(c, "demo_nvda")
    record = c.repos.investigations.get("demo_nvda")
    assert record is not None
    if record.audio_key:
        (PUBLIC / "investigation.wav").write_bytes(downsample_wav(c.storage.get_bytes(record.audio_key)))
    if record.infographic_key:
        (PUBLIC / "visual-brief.png").write_bytes(c.storage.get_bytes(record.infographic_key))
    data = record.model_dump(mode="json", exclude={"user_id", "audio_key", "infographic_key"})
    dump("investigation.json", {"investigation": data, "events": events_for(c, "demo_nvda")})
    if record.result and record.result.news:
        dump("news.json", [a.model_dump(mode="json") for a in record.result.news.articles])
    if record.result and record.result.financial:
        dump("financials.json", record.result.financial.model_dump(mode="json"))

    print("2/4 Multimodal research (earnings call + PDF)…")
    attachments = []
    for kind, fname, mime in (("audio", "earnings_call.wav", "audio/wav"), ("document", "northwind_q3_fy2026_results.pdf", "application/pdf")):
        raw = (DEMO / fname).read_bytes()
        key = f"users/{USER}/uploads/{kind}/up_demo_{kind}/{fname}"
        c.storage.put_bytes(key, raw, mime)
        attachments.append(AttachmentRef(upload_id=f"up_demo_{kind}", kind=kind, filename=fname, content_type=mime, storage_key=key, size_bytes=len(raw)))  # type: ignore[arg-type]
    now = utc_now_iso()
    c.repos.investigations.put(InvestigationRecord(
        investigation_id="demo_call", user_id=USER, question="Summarize this earnings call and the results release. Does it change the thesis?",
        attachments=attachments, created_at=now, updated_at=now,
    ))
    await run_investigation(c, "demo_call")
    call = c.repos.investigations.get("demo_call")
    assert call and call.status == "completed", call.error if call else "missing"
    transcript = None
    if call.result and call.result.audio and call.result.audio[0].transcript_key:
        transcript = json.loads(c.storage.get_bytes(call.result.audio[0].transcript_key))
    dump("investigation_multimodal.json", {
        "investigation": call.model_dump(mode="json", exclude={"user_id", "audio_key", "infographic_key"}),
        "events": events_for(c, "demo_call"),
        "transcript": transcript,
    })

    await record_video(c)

    print("3/4 Daily briefing…")
    c.repos.briefings.put(Briefing(briefing_id="demo_briefing", user_id=USER, date=utc_now_iso()[:10], briefing_type="daily",
                                   audio_status="pending", email_status="not_requested", created_at=utc_now_iso()))
    await run_briefing(c, "demo_briefing", with_audio=True, send_email=False)
    briefing = c.repos.briefings.get("demo_briefing")
    assert briefing and briefing.status == "completed"
    if briefing.audio_key:
        (PUBLIC / "briefing.wav").write_bytes(downsample_wav(c.storage.get_bytes(briefing.audio_key)))
    _, html, _ = render_briefing_email(briefing, frontend_url="https://signalroom.example", audio_url="/demo/briefing.wav" if briefing.audio_key else None)
    (DEMO / "email_preview.html").write_text(html, encoding="utf-8")
    dump("briefing.json", briefing.model_dump(mode="json", exclude={"user_id", "audio_key"}))

    print("4/4 Market snapshots…")
    details = {}
    for symbol, _, _ in DEMO_WATCHLIST:
        details[symbol] = {}
        for rng in ("1d", "5d", "1mo", "1y"):
            try:
                details[symbol][rng] = (await assets.detail(symbol, rng, USER)).model_dump(mode="json")  # type: ignore[arg-type]
            except Exception as exc:  # keep recording other symbols
                print(f"   skipped {symbol} {rng}: {type(exc).__name__}")
    watchlist = [w.model_dump(mode="json") for w in await WatchlistService(c.repos.watchlists, assets, 20).list_items(USER)]
    overview = (await assets.overview()).model_dump(mode="json")
    search = [m.model_dump(mode="json") for q in ("nvidia", "tesla", "apple", "bitcoin", "microsoft", "s&p") for m in await assets.search(q)]
    dump("assets.json", {"recorded_at": utc_now_iso(), "watchlist": watchlist, "overview": overview, "details": details, "search": search})
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
