"""Generate the synthetic multi-voice earnings-call audio used in the demo.

Reads demo_data/earnings_call.txt (SPEAKER|VOICE|TEXT lines about a FICTIONAL company),
synthesises each turn with the configured TTS model (via the AIGateway: OpenRouter
`openai/gpt-audio-mini` by default, or Gemini TTS with GEMINI_API_KEY) and writes
demo_data/earnings_call.wav. No copyrighted audio is used.

Usage (from the repo root):
    backend/.venv/Scripts/python scripts/generate_demo_audio.py      # Windows
    backend/.venv/bin/python scripts/generate_demo_audio.py          # macOS/Linux
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.integrations.ai.audio_utils import pcm16_duration_seconds, pcm16_to_wav, silence  # noqa: E402
from app.integrations.ai.gateway import RoleBinding  # noqa: E402

STYLE = "natural conference-call delivery, clear and professional"


async def main() -> None:
    from app.container import get_container

    container = get_container()
    ai = container.ai
    if not ai.available("tts"):
        raise SystemExit("No TTS model configured. Set OPENROUTER_API_KEY (or GEMINI_API_KEY) in .env")
    binding: RoleBinding = ai._binding("tts")
    lines = [
        line.split("|", 2)
        for line in (ROOT / "demo_data" / "earnings_call.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    pcm = bytearray()
    for idx, (speaker, voice, text) in enumerate(lines):
        print(f"[{idx + 1}/{len(lines)}] {speaker} ({voice})")
        result = await binding.provider.synthesize(text, model=binding.model, voice=voice, style=STYLE)
        if idx:
            pcm.extend(silence(0.6, result.sample_rate))
        pcm.extend(result.pcm)
    out = ROOT / "demo_data" / "earnings_call.wav"
    out.write_bytes(pcm16_to_wav(bytes(pcm), 24000))
    print(f"Wrote {out} ({pcm16_duration_seconds(bytes(pcm)):.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
