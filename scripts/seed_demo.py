"""Seed a demo user into the configured backend (local mode by default) with recorded real runs.

Creates demo@signalroom.ai / DemoPassw0rd (local auth), the demo watchlist, the recorded
NVIDIA, multimodal (call + PDF) and video-webinar investigations and the recorded briefing
(with audio), so the full UI can be explored instantly. Each investigation is also indexed
for semantic search (a fraction of a cent of embeddings; keyword index without an API key).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.container import get_container  # noqa: E402
from app.schemas.assets import WatchlistItem  # noqa: E402
from app.schemas.briefings import Briefing  # noqa: E402
from app.schemas.investigations import InvestigationEvent, InvestigationRecord  # noqa: E402
from app.schemas.users import UserRecord  # noqa: E402
from app.services.local_auth import LocalAuthService  # noqa: E402
from app.services.watchlist_service import DEMO_WATCHLIST  # noqa: E402
from app.utils.time import utc_now_iso  # noqa: E402

EMAIL, PASSWORD = "demo@signalroom.ai", "DemoPassw0rd"
DEMO = ROOT / "demo_data"
PUBLIC = ROOT / "frontend" / "public" / "demo"


def main() -> None:
    c = get_container()
    auth = LocalAuthService(c.repos.credentials, c.settings.local_jwt_secret.get_secret_value(), 60)
    existing = c.repos.credentials.get(EMAIL)
    user_id = existing["user_id"] if existing else auth.signup(EMAIL, PASSWORD)[1]
    if not c.repos.users.get(user_id):
        c.repos.users.put(UserRecord(user_id=user_id, email=EMAIL, created_at=utc_now_iso()))
    if not c.repos.watchlists.list(user_id):
        for i, (sym, name, kind) in enumerate(DEMO_WATCHLIST):
            c.repos.watchlists.put(WatchlistItem(user_id=user_id, symbol=sym, display_name=name, asset_type=kind, position=i, added_at=utc_now_iso()))  # type: ignore[arg-type]

    for fname, audio in (("investigation.json", "investigation.wav"), ("investigation_multimodal.json", None), ("investigation_video.json", None)):
        if not (DEMO / fname).exists():
            continue
        data = json.loads((DEMO / fname).read_text(encoding="utf-8"))
        rec = InvestigationRecord.model_validate({**data["investigation"], "user_id": user_id})
        media = [*rec.result.audio, *rec.result.videos] if rec.result else []
        for clip in media:  # recorded transcripts move under the seeded user (private keys are per user)
            if data.get("transcript"):
                clip.transcript_key = f"users/{user_id}/investigations/{rec.investigation_id}/output/transcripts/{clip.upload_id}.json"
                c.storage.put_bytes(clip.transcript_key, json.dumps(data["transcript"]).encode("utf-8"), "application/json")
        if audio and (PUBLIC / audio).exists():
            key = f"users/{user_id}/investigations/{rec.investigation_id}/output/audio/brief.wav"
            c.storage.put_bytes(key, (PUBLIC / audio).read_bytes(), "audio/wav")
            rec.audio_key, rec.audio_status = key, "ready"
        if rec.infographic_status == "ready" and (PUBLIC / "visual-brief.png").exists():
            key = f"users/{user_id}/investigations/{rec.investigation_id}/output/images/visual-brief.png"
            c.storage.put_bytes(key, (PUBLIC / "visual-brief.png").read_bytes(), "image/png")
            rec.infographic_key = key
        c.repos.investigations.put(rec)
        if not c.repos.events.list_after(rec.investigation_id):
            for e in data["events"]:
                c.repos.events.append(InvestigationEvent.model_validate(e))
        asyncio.run(c.search_index().index_safely(rec))
        print("seeded", rec.investigation_id)

    b = Briefing.model_validate({**json.loads((DEMO / "briefing.json").read_text(encoding="utf-8")), "user_id": user_id})
    if (PUBLIC / "briefing.wav").exists():
        key = f"users/{user_id}/briefings/{b.briefing_id}/output/briefing.wav"
        c.storage.put_bytes(key, (PUBLIC / "briefing.wav").read_bytes(), "audio/wav")
        b.audio_key, b.audio_status = key, "ready"
    c.repos.briefings.put(b)
    print(f"Demo account ready: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
