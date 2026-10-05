"""Rebuild the semantic-search index of a user's investigations (e.g. after changing the embedding model).

Usage (repo root; reads the same configuration as the backend, local or AWS):
    backend/.venv/Scripts/python scripts/reindex.py demo@signalroom.ai
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.container import get_container  # noqa: E402


async def main(email: str) -> None:
    c = get_container()
    cred = c.repos.credentials.get(email.lower())
    user_id = cred["user_id"] if cred else email  # Cognito users: pass the user id (sub) directly
    search = c.search_index()
    print(f"Embedding model: {c.ai.model_for('embedding') or 'none (keyword index)'}")
    for rec in c.repos.investigations.list_by_user(user_id, 200):
        if rec.status != "completed":
            continue
        index = await search.index(rec)
        print(f"  {rec.investigation_id}: {len(index.chunks) if index else 0} passages")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1]))
