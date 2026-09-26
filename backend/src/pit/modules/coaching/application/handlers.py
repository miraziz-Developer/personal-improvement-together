"""The coach reacts to what happens in the user's challenge and says something useful."""

from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from pit.modules.challenges.domain.events import (
    DayCompleted,
    DayFrozen,
    GroupMemberJoined,
    ParticipationCompleted,
    ParticipationFailed,
    ParticipationStarted,
)
from pit.modules.challenges.domain.participation import (
    DayStatus,
    Participation,
    ParticipationStatus,
)
from pit.modules.challenges.domain.repositories import ChallengeRepository, ParticipationRepository
from pit.modules.coaching.application.commands import MarkNotificationsRead, SendDailyNudges
from pit.modules.coaching.domain.messages import STREAK_MILESTONES, Moment, compose
from pit.modules.coaching.domain.notification import Notification
from pit.modules.coaching.domain.repositories import NotificationRepository
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.verification.domain.events import ProofRejected, ProofSentToReview
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction

_NAMESPACE = uuid5(NAMESPACE_URL, "pit:notification")


class CoachingUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def challenges(self) -> ChallengeRepository: ...

    @property
    def participations(self) -> ParticipationRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...


async def _notify(
    uow: CoachingUoW,
    clock: Clock,
    *,
    key: str,
    user_id: UUID,
    moment: Moment,
    participation_id: UUID | None,
    **facts: object,
) -> None:
    # The id is derived from the moment, so a retried handler or job never sends twice.
    notification_id = uuid5(_NAMESPACE, key)
    if await uow.notifications.get(notification_id) is not None:
        return
    title, body = compose(moment, seed=key, **facts)
    uow.notifications.add(
        Notification.create(
            notification_id=notification_id,
            user_id=user_id,
            moment=moment,
            title=title,
            body=body,
            created_at=clock.now(),
            participation_id=participation_id,
        )
    )


def _days_left(participation: Participation) -> int:
    return sum(
        1
        for s in participation.days.values()
        if s in (DayStatus.PENDING, DayStatus.AWAITING_REVIEW)
    )


async def _context(uow: CoachingUoW, participation_id: UUID) -> tuple[Participation, str, str]:
    participation = require(await uow.participations.get(participation_id), "Challenge topilmadi")
    user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
    challenge = require(await uow.challenges.get(participation.challenge_id), "Challenge topilmadi")
    return participation, user.username, challenge.title


async def on_started(event: ParticipationStarted, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation, name, title = await _context(uow, event.participation_id)
        await _notify(
            uow,
            clock,
            key=f"started:{event.participation_id}",
            user_id=event.user_id,
            moment=Moment.CHALLENGE_STARTED,
            participation_id=event.participation_id,
            name=name,
            title=title,
            days=len(participation.days),
        )
        await uow.commit()


async def on_day_completed(event: DayCompleted, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation, name, _ = await _context(uow, event.participation_id)
        if participation.status is ParticipationStatus.COMPLETED:
            return  # the completion message says it all
        milestone = event.streak in STREAK_MILESTONES
        await _notify(
            uow,
            clock,
            key=f"day:{event.participation_id}:{event.day.isoformat()}",
            user_id=event.user_id,
            moment=Moment.STREAK_MILESTONE if milestone else Moment.DAY_DONE,
            participation_id=event.participation_id,
            name=name,
            streak=event.streak,
            days_left=_days_left(participation),
        )
        await uow.commit()


async def on_day_frozen(event: DayFrozen, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation, name, _ = await _context(uow, event.participation_id)
        await _notify(
            uow,
            clock,
            key=f"frozen:{event.participation_id}:{event.day.isoformat()}",
            user_id=event.user_id,
            moment=Moment.DAY_FROZEN,
            participation_id=event.participation_id,
            name=name,
            freezes_left=participation.freezes_left,
        )
        await uow.commit()


async def on_failed(event: ParticipationFailed, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation, name, _ = await _context(uow, event.participation_id)
        await _notify(
            uow,
            clock,
            key=f"failed:{event.participation_id}",
            user_id=event.user_id,
            moment=Moment.CHALLENGE_FAILED,
            participation_id=event.participation_id,
            name=name,
            done=participation.days_completed,
        )
        await uow.commit()


async def on_completed(event: ParticipationCompleted, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        _, name, title = await _context(uow, event.participation_id)
        money_line = "" if event.stake.is_zero else f"Garovingiz ({event.stake}) to'liq qaytarildi."
        await _notify(
            uow,
            clock,
            key=f"completed:{event.participation_id}",
            user_id=event.user_id,
            moment=Moment.CHALLENGE_COMPLETED,
            participation_id=event.participation_id,
            name=name,
            title=title,
            money_line=money_line,
        )
        await uow.commit()


async def on_proof_rejected(event: ProofRejected, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        await _notify(
            uow,
            clock,
            key=f"rejected:{event.proof_id}",
            user_id=event.user_id,
            moment=Moment.PROOF_REJECTED,
            participation_id=event.participation_id,
            reason=(event.reason or "isbot talabga mos kelmadi").rstrip("."),
        )
        await uow.commit()


async def on_proof_in_review(event: ProofSentToReview, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation = require(
            await uow.participations.get(event.participation_id), "Challenge topilmadi"
        )
        await _notify(
            uow,
            clock,
            key=f"review:{event.proof_id}",
            user_id=participation.user_id,
            moment=Moment.PROOF_IN_REVIEW,
            participation_id=event.participation_id,
        )
        await uow.commit()


async def _group_mates(uow: CoachingUoW, group_id: UUID, besides_user: UUID) -> list[Participation]:
    """The other members' open runs in the group — who should hear about a friend's news."""
    mates = []
    for participation_id in await uow.participations.list_in_group(group_id):
        mate = await uow.participations.get(participation_id)
        if mate is not None and mate.is_open and mate.user_id != besides_user:
            mates.append(mate)
    return mates


async def on_friend_day_done(event: DayCompleted, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        participation, name, _ = await _context(uow, event.participation_id)
        if participation.group_id is None:
            return
        for mate in await _group_mates(uow, participation.group_id, participation.user_id):
            await _notify(
                uow,
                clock,
                key=f"friend-day:{participation.id}:{event.day.isoformat()}:{mate.id}",
                user_id=mate.user_id,
                moment=Moment.FRIEND_DAY_DONE,
                participation_id=mate.id,
                friend=name,
                streak=event.streak,
            )
        await uow.commit()


async def on_friend_joined(event: GroupMemberJoined, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        friend = require(await uow.users.get(event.user_id), "Foydalanuvchi topilmadi")
        challenge = require(await uow.challenges.get(event.challenge_id), "Challenge topilmadi")
        for mate in await _group_mates(uow, event.group_id, event.user_id):
            await _notify(
                uow,
                clock,
                key=f"friend-joined:{event.group_id}:{event.user_id}:{mate.id}",
                user_id=mate.user_id,
                moment=Moment.FRIEND_JOINED,
                participation_id=mate.id,
                friend=friend.username,
                title=challenge.title,
            )
        await uow.commit()


async def send_daily_nudges(cmd: SendDailyNudges, uow: CoachingUoW, *, clock: Clock) -> int:
    sent = 0
    async with uow:
        for participation_id in await uow.participations.list_open_ids():
            participation, name, _ = await _context(uow, participation_id)
            if participation.status is not ParticipationStatus.ACTIVE:
                continue
            user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
            today = local_date(clock.now(), user.timezone)
            tasks = participation.tasks_on(today)
            common = {"user_id": user.id, "participation_id": participation_id}
            if cmd.kind == "morning" and not tasks:
                key = f"rest:{participation_id}:{today.isoformat()}"
                await _notify(uow, clock, key=key, moment=Moment.REST_DAY, **common)
            elif cmd.kind == "morning":
                await _notify(
                    uow,
                    clock,
                    key=f"morning:{participation_id}:{today.isoformat()}",
                    moment=Moment.MORNING,
                    name=name,
                    tasks=len(tasks),
                    minutes=sum(t.minutes for t in tasks),
                    streak=participation.current_streak,
                    **common,
                )
            elif participation.days.get(today) is DayStatus.PENDING:
                await _notify(
                    uow,
                    clock,
                    key=f"evening:{participation_id}:{today.isoformat()}",
                    moment=Moment.EVENING_REMINDER,
                    name=name,
                    left=len(participation.required_tasks(today)),
                    streak=participation.current_streak,
                    **common,
                )
            else:
                continue
            sent += 1
        await uow.commit()
    return sent


async def mark_read(cmd: MarkNotificationsRead, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        for notification_id in cmd.notification_ids:
            notification = await uow.notifications.get(notification_id)
            if notification is not None and notification.user_id == cmd.user_id:
                notification.mark_read(clock.now())
        await uow.commit()
