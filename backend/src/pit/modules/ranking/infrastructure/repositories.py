from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pit.modules.ranking.domain.scoring import ScoreEntry
from pit.modules.ranking.infrastructure.tables import score_entries


class SqlScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, entry: ScoreEntry) -> bool:
        statement = (
            insert(score_entries)
            .values(
                source_key=entry.source_key,
                user_id=entry.user_id,
                points=entry.points,
                reason=entry.reason.value,
                earned_on=entry.earned_on,
            )
            .on_conflict_do_nothing(index_elements=["source_key"])
            .returning(score_entries.c.source_key)
        )
        return (await self._session.execute(statement)).first() is not None
