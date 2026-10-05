"""Voice Agent — turns a written brief into calm, professional narration (TTS) stored privately."""

from __future__ import annotations

import asyncio
import re

from app.integrations.ai.gateway import AIGateway
from app.integrations.storage.base import StorageBackend

NARRATION_STYLE = (
    "calm, confident, analytical, measured pace, professional financial news anchor, not sensationalist"
)


def speakable(text: str) -> str:
    """Make numbers and symbols read naturally (e.g. '-2.13%' → 'minus 2.13 percent')."""
    text = re.sub(r"(?<![\w.])-(\d)", r"minus \1", text)
    text = re.sub(r"\+(\d)", r"plus \1", text)
    text = text.replace("%", " percent").replace("&", " and ").replace("^GSPC", "the S&P 500")
    text = re.sub(r"\bpp\b", "percentage points", text)
    return re.sub(r"\s{2,}", " ", text).strip()


async def narrate(
    ai: AIGateway, storage: StorageBackend, script: str, key: str, agent: str = "voice"
) -> float:
    """Synthesize `script`, store WAV at `key`, return duration in seconds."""
    output = await ai.speech(speakable(script), agent=agent, style=NARRATION_STYLE)
    await asyncio.to_thread(storage.put_bytes, key, output.wav, "audio/wav")
    return output.duration_seconds


def investigation_script(
    asset: str, summary: str, what_happened: str, drivers: list[tuple[str, float, str]], watch: list[str]
) -> str:
    parts = [f"SignalRoom research brief on {asset}.", summary]
    if what_happened:
        parts.append(what_happened)
    if drivers:
        parts.append("Likely drivers, by evidence-weighted contribution.")
        for name, score, explanation in drivers[:3]:
            parts.append(f"{name}, about {round(score)} percent. {explanation}")
    if watch:
        parts.append("What to watch: " + "; ".join(watch[:3]) + ".")
    parts.append("This is an educational research prototype, not investment advice.")
    return "\n\n".join(p for p in parts if p)
