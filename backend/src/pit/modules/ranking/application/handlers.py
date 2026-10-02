from typing import Protocol

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.events import (
    DayCompleted,
    FriendBrought,
    OptionalTaskCompleted,
    ParticipationCompleted,
)
from pit.modules.identity.domain.events import AccountErased
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.ranking.application.ports import LeaderboardIndex
from pit.modules.ranking.domain.repositories import ScoreRepository
from pit.modules.ranking.domain.scoring import (
    FRIEND_POINTS,
    ScoreEntry,
    ScoreReason,
    completion_bonus,
    day_points,
    leaderboard_keys,
    optional_task_points,
)
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction


class RankingUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def scores(self) -> ScoreRepository: ...


async def award_day_points(
    event: DayCompleted, uow: RankingUoW, *, index: LeaderboardIndex
) -> None:
    entry = ScoreEntry(
        user_id=event.user_id,
        points=day_points(event.difficulty, event.streak),
        reason=ScoreReason.DAY,
        source_key=f"day:{event.participation_id}:{event.day.isoformat()}",
        earned_on=event.day,
    )
    await _award(entry, uow, index)


async def award_completion_bonus(
    event: ParticipationCompleted, uow: RankingUoW, *, index: LeaderboardIndex
) -> None:
    entry = ScoreEntry(
        user_id=event.user_id,
        points=completion_bonus(
            event.difficulty, event.duration_days, stake_mode=event.mode is ParticipationMode.STAKE
        ),
        reason=ScoreReason.COMPLETION,
        source_key=f"completion:{event.participation_id}",
        earned_on=event.finished_on,
    )
    await _award(entry, uow, index)


async def award_optional_task_points(
    event: OptionalTaskCompleted, uow: RankingUoW, *, index: LeaderboardIndex
) -> None:
    entry = ScoreEntry(
        user_id=event.user_id,
        points=optional_task_points(event.minutes),
        reason=ScoreReason.OPTIONAL_TASK,
        source_key=f"task:{event.participation_id}:{event.day.isoformat()}:{event.task_key}",
        earned_on=event.day,
    )
    await _award(entry, uow, index)


async def award_friend_points(
    event: FriendBrought, uow: RankingUoW, *, index: LeaderboardIndex
) -> None:
    entry = ScoreEntry(
        user_id=event.user_id,
        points=FRIEND_POINTS,
        reason=ScoreReason.FRIEND,
        source_key=f"friend:{event.friend_participation_id}",  # once per friend's run
        earned_on=event.day,
    )
    await _award(entry, uow, index)


async def _award(entry: ScoreEntry, uow: RankingUoW, index: LeaderboardIndex) -> None:
    async with uow:
        user = require(await uow.users.get(entry.user_id), "Foydalanuvchi topilmadi")
        added = await uow.scores.add_if_absent(entry)
        await uow.commit()
    if added:
        # After commit: Postgres is the truth; a lost call is fixed by the nightly Redis rebuild.
        keys = leaderboard_keys(
            day=entry.earned_on, birth_year=user.birth_year, region_id=user.region_id
        )
        await index.increment(keys, entry.user_id, entry.points)


async def drop_from_leaderboards(
    event: AccountErased, uow: Transaction, *, index: LeaderboardIndex
) -> None:
    """Erased users leave the boards; their points stay in the ledger of scores, anonymous."""
    await index.remove_user(event.user_id)
