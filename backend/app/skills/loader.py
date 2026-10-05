"""Skill library with progressive disclosure.

Agents load only the concise `SKILL.md` into their prompt. Detailed methodology in
`references/` is loaded explicitly, only by the agents/situations that need it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"Unknown skill: {name}")
    text = path.read_text(encoding="utf-8")
    # Drop YAML front matter from the prompt version.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return text.strip()


@lru_cache(maxsize=64)
def load_reference(skill: str, reference: str) -> str:
    path = SKILLS_DIR / skill / "references" / reference
    if not path.exists():
        raise FileNotFoundError(f"Unknown reference {skill}/{reference}")
    return path.read_text(encoding="utf-8").strip()


def list_skills() -> list[str]:
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
