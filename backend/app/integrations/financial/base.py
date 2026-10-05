from __future__ import annotations

from typing import Protocol

from app.schemas.agents import FinancialSnapshot


class FinancialDataError(Exception):
    pass


class FinancialDataProvider(Protocol):
    name: str

    async def snapshot(self, symbol: str) -> FinancialSnapshot: ...
