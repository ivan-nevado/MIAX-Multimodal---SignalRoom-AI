"""Prompts live in .txt files next to this module (not in Python f-strings)."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.skills.loader import load_skill

PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Unknown prompt: {name}")
    return path.read_text(encoding="utf-8").strip()


def system_prompt(name: str, *skills: str) -> str:
    """Agent prompt + the concise SKILL.md of each skill it relies on.

    The current date is always included: models otherwise treat recent data as "future" or stale.
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    parts = [
        f"Current date (UTC): {today}. All provided data is real and current unless stated otherwise.\n\n",
        load_prompt(name),
    ]
    for skill in skills:
        parts.append(f"\n\n## Skill: {skill}\n{load_skill(skill)}")
    return "".join(parts)
