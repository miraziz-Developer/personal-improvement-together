from typing import Protocol
from uuid import UUID


class LeaderboardIndex(Protocol):
    """Fast leaderboard projection (Redis sorted sets in production)."""

    async def increment(self, keys: list[str], user_id: UUID, points: int) -> None: ...
