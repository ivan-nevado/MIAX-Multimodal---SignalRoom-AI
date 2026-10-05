from __future__ import annotations

from typing import Protocol

from app.schemas.agents import MacroIndicator


class MacroDataError(Exception):
    pass


class MacroDataProvider(Protocol):
    name: str

    async def indicators(self) -> list[MacroIndicator]: ...
