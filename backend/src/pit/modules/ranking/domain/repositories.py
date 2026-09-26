from typing import Protocol

from pit.modules.ranking.domain.scoring import ScoreEntry


class ScoreRepository(Protocol):
    """Source of truth for points; Redis leaderboards are a rebuildable projection of it."""

    async def add_if_absent(self, entry: ScoreEntry) -> bool: ...
