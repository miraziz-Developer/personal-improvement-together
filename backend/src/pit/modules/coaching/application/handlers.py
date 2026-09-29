"""The coach reacts to what happens in the user's challenge and says something useful."""

from datetime import date, datetime, timedelta
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from pit.modules.challenges.domain.challenge import Challenge
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
from pit.modules.challenges.domain.roadmap import DAYS_PER_MONTH
from pit.modules.coaching.application.commands import (
    CheerFriend,
    MarkNotificationsRead,
    SendDailyNudges,
    SendTaskReminders,
    SendWeeklySummaries,
)
from pit.modules.coaching.application.ports import ChallengeTexts, OwnTexts
from pit.modules.coaching.domain.messages import STREAK_MILESTONES, Moment, compose
from pit.modules.coaching.domain.notification import Notification
from pit.modules.coaching.domain.repositories import NotificationRepository
from pit.modules.identity.domain.events import AccountErased
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.identity.domain.user import User
from pit.modules.planning.domain.repositories import LifePlanRepository
from pit.modules.verification.domain.events import ProofRejected, ProofSentToReview
from pit.modules.verification.domain.repositories import ProofRepository
from pit.modules.verification.domain.verdict import ProofStatus
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.errors import DomainError, PermissionDenied

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

    @property
    def proofs(self) -> ProofRepository: ...

    @property
    def life_plans(self) -> LifePlanRepository: ...


REMINDER_WINDOW = timedelta(minutes=30)  # a reminder later than this would only nag
_OWN_TEXTS = OwnTexts()


def _focus_text(
    texts: ChallengeTexts, challenge: Challenge, p: Participation, day: date, locale: str
) -> str | None:
    """Today's lesson, or the week's theme when no lesson is written for today."""
    roadmap = texts.roadmap(challenge, locale)
    focus = roadmap.focus(p.start_date, p.days, day) if roadmap else None
    return (focus.lesson or focus.theme) if focus else None


async def _notify(
    uow: CoachingUoW,
    clock: Clock,
    *,
    key: str,
    user_id: UUID,
    moment: Moment,
    participation_id: UUID | None,
    subject_id: UUID | None = None,
    **facts: object,
) -> None:
    # The id is derived from the moment, so a retried handler or job never sends twice.
    notification_id = uuid5(_NAMESPACE, key)
    if await uow.notifications.get(notification_id) is not None:
        return
    reader = await uow.users.get(user_id)
    locale = reader.locale.value if reader else "uz"
    title, body = compose(moment, seed=key, locale=locale, **facts)
    uow.notifications.add(
        Notification.create(
            notification_id=notification_id,
            user_id=user_id,
            moment=moment,
            title=title,
            body=body,
            created_at=clock.now(),
            participation_id=participation_id,
            subject_id=subject_id,
        )
    )


def _days_left(participation: Participation) -> int:
    return sum(
        1
        for s in participation.days.values()
        if s in (DayStatus.PENDING, DayStatus.AWAITING_REVIEW)
    )


async def _context(
    uow: CoachingUoW, participation_id: UUID, texts: ChallengeTexts = _OWN_TEXTS
) -> tuple[Participation, str, str]:
    """The run, its owner's name and the challenge title in the owner's language."""
    participation = require(await uow.participations.get(participation_id), "Challenge topilmadi")
    user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
    challenge = require(await uow.challenges.get(participation.challenge_id), "Challenge topilmadi")
    return participation, user.username, texts.title(challenge, user.locale.value)


async def on_started(
    event: ParticipationStarted,
    uow: CoachingUoW,
    *,
    clock: Clock,
    texts: ChallengeTexts = _OWN_TEXTS,
) -> None:
    async with uow:
        participation, name, title = await _context(uow, event.participation_id, texts)
        await _notify(
            uow,
            clock,
            key=f"started:{event.participation_id}",
            user_id=event.user_id,
            moment=Moment.CHALLENGE_STARTED,
            participation_id=event.participation_id,
            name=name,
            title=title,
            days=participation.total_days,
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


async def on_completed(
    event: ParticipationCompleted,
    uow: CoachingUoW,
    *,
    clock: Clock,
    texts: ChallengeTexts = _OWN_TEXTS,
) -> None:
    async with uow:
        _, name, title = await _context(uow, event.participation_id, texts)
        await _notify(
            uow,
            clock,
            key=f"completed:{event.participation_id}",
            user_id=event.user_id,
            moment=Moment.CHALLENGE_COMPLETED,
            participation_id=event.participation_id,
            name=name,
            title=title,
            stake="" if event.stake.is_zero else str(event.stake),
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
                subject_id=participation.user_id,
                friend=name,
                streak=event.streak,
            )
        await uow.commit()


async def on_friend_joined(
    event: GroupMemberJoined,
    uow: CoachingUoW,
    *,
    clock: Clock,
    texts: ChallengeTexts = _OWN_TEXTS,
) -> None:
    async with uow:
        friend = require(await uow.users.get(event.user_id), "Foydalanuvchi topilmadi")
        challenge = require(await uow.challenges.get(event.challenge_id), "Challenge topilmadi")
        for mate in await _group_mates(uow, event.group_id, event.user_id):
            reader = await uow.users.get(mate.user_id)
            await _notify(
                uow,
                clock,
                key=f"friend-joined:{event.group_id}:{event.user_id}:{mate.id}",
                user_id=mate.user_id,
                moment=Moment.FRIEND_JOINED,
                participation_id=mate.id,
                friend=friend.username,
                title=texts.title(challenge, reader.locale.value if reader else "uz"),
            )
        await uow.commit()


async def send_daily_nudges(
    cmd: SendDailyNudges, uow: CoachingUoW, *, clock: Clock, texts: ChallengeTexts = _OWN_TEXTS
) -> int:
    if cmd.kind == "morning":
        return await _send_mornings(uow, clock, texts)
    sent = 0
    async with uow:
        for participation_id in await uow.participations.list_open_ids():
            participation, name, _ = await _context(uow, participation_id)
            if participation.status is not ParticipationStatus.ACTIVE:
                continue
            user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
            today = local_date(clock.now(), user.timezone)
            if participation.days.get(today) is not DayStatus.PENDING:
                continue
            await _notify(
                uow,
                clock,
                key=f"evening:{participation_id}:{today.isoformat()}",
                user_id=user.id,
                participation_id=participation_id,
                moment=Moment.EVENING_REMINDER,
                name=name,
                left=len(participation.required_tasks(today)),
                streak=participation.current_streak,
            )
            sent += 1
        await uow.commit()
    return sent


async def _runs_by_user(uow: CoachingUoW) -> dict[UUID, list[tuple[Participation, Challenge]]]:
    runs: dict[UUID, list[tuple[Participation, Challenge]]] = {}
    for participation_id in await uow.participations.list_open_ids():
        participation = await uow.participations.get(participation_id)
        if participation is None or participation.status is not ParticipationStatus.ACTIVE:
            continue
        challenge = require(
            await uow.challenges.get(participation.challenge_id), "Challenge topilmadi"
        )
        runs.setdefault(participation.user_id, []).append((participation, challenge))
    return runs


def _first_task(
    texts: ChallengeTexts, runs: list[tuple[Participation, Challenge]], day: date, locale: str
) -> str | None:
    """The day's first task, "07:00 — Running" when it has a time."""
    tasks = [(t, c) for p, c in runs for t in p.tasks_on(day)]
    if not tasks:
        return None
    timed = sorted((item for item in tasks if item[0].at), key=lambda item: item[0].at or 0)
    task, challenge = timed[0] if timed else tasks[0]
    title = texts.task_title(challenge, task, locale)
    return f"{task.at.strftime('%H:%M')} — {title}" if task.at else title


async def _morning_for(
    uow: CoachingUoW,
    clock: Clock,
    texts: ChallengeTexts,
    user: User,
    mine: list[tuple[Participation, Challenge]],
    today: date,
) -> int:
    """One morning message for one person (ids make a repeat a no-op)."""
    locale = user.locale.value
    sent = await _month_milestones(uow, clock, texts, user.id, mine, today, locale)
    working = [(p, c) for p, c in mine if p.tasks_on(today)]
    if not working:
        only = mine[0][0] if len(mine) == 1 else None
        await _notify(
            uow,
            clock,
            key=f"rest:{only.id if only else user.id}:{today.isoformat()}",
            user_id=user.id,
            participation_id=only.id if only else None,
            moment=Moment.REST_DAY,
        )
        return sent + 1
    focus = next((f for p, c in working if (f := _focus_text(texts, c, p, today, locale))), None)
    tasks = [t for p, _ in working for t in p.tasks_on(today)]
    if len(working) == 1:
        participation = working[0][0]
        await _notify(
            uow,
            clock,
            key=f"morning:{participation.id}:{today.isoformat()}",
            user_id=user.id,
            participation_id=participation.id,
            moment=Moment.MORNING,
            name=user.username,
            tasks=len(tasks),
            minutes=sum(t.minutes for t in tasks),
            streak=participation.current_streak,
            focus=focus,
        )
    else:
        await _notify(
            uow,
            clock,
            key=f"routine:{user.id}:{today.isoformat()}",
            user_id=user.id,
            participation_id=None,
            moment=Moment.MORNING_ROUTINE,
            name=user.username,
            goals=len(working),
            tasks=len(tasks),
            minutes=sum(t.minutes for t in tasks),
            first=_first_task(texts, working, today, locale),
            focus=focus,
        )
    return sent + 1


async def _send_mornings(uow: CoachingUoW, clock: Clock, texts: ChallengeTexts) -> int:
    """The fixed 08:00 morning message. People with a daily routine get theirs when they
    wake up instead (see _routine_moments), unless they are up before 08:00 anyway."""
    sent = 0
    async with uow:
        for user_id, mine in (await _runs_by_user(uow)).items():
            user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
            now = clock.now().astimezone(ZoneInfo(user.timezone))
            routine = await uow.life_plans.latest_started(user_id)
            if routine is not None and routine.frame.wake > now.time():
                continue  # still asleep: the message comes at wake-up time
            sent += await _morning_for(uow, clock, texts, user, mine, now.date())
        await uow.commit()
    return sent


WAKE_WINDOW = timedelta(minutes=30)
SUMMARY_BEFORE_SLEEP = (timedelta(minutes=45), timedelta(minutes=15))


async def _routine_moments(uow: CoachingUoW, clock: Clock, texts: ChallengeTexts) -> int:
    """For people with a daily routine: the morning message at wake-up time, and a short
    summary of the day before they go to sleep. Called from the few-minute tick."""
    sent = 0
    for user_id, mine in (await _runs_by_user(uow)).items():
        routine = await uow.life_plans.latest_started(user_id)
        if routine is None:
            continue
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        now = clock.now().astimezone(ZoneInfo(user.timezone))
        today, clock_now = now.date(), now.replace(tzinfo=None)
        wake = datetime.combine(today, routine.frame.wake)
        if wake <= clock_now < wake + WAKE_WINDOW:
            sent += await _morning_for(uow, clock, texts, user, mine, today)
        sleep = datetime.combine(today, routine.frame.sleep)
        if routine.frame.sleeps_after_midnight:
            sleep += timedelta(days=1)
        if sleep - SUMMARY_BEFORE_SLEEP[0] <= clock_now < sleep - SUMMARY_BEFORE_SLEEP[1]:
            sent += await _day_summary(uow, clock, texts, user, mine, today)
    return sent


async def _day_summary(
    uow: CoachingUoW,
    clock: Clock,
    texts: ChallengeTexts,
    user: User,
    mine: list[tuple[Participation, Challenge]],
    today: date,
) -> int:
    planned = done = 0
    for participation, _ in mine:
        required = [t for t in participation.tasks_on(today) if t.required]
        if not required:
            continue
        proofs = await uow.proofs.list_for_day(participation.id, today)
        handled = {p.task_key for p in proofs if p.status is not ProofStatus.REJECTED}
        planned += len(required)
        done += sum(1 for t in required if t.key in handled)
    if planned == 0:
        return 0
    await _notify(
        uow,
        clock,
        key=f"summary:{user.id}:{today.isoformat()}",
        user_id=user.id,
        participation_id=None,
        moment=Moment.DAY_SUMMARY,
        name=user.username,
        done=done,
        planned=planned,
        tomorrow=_first_task(texts, mine, today + timedelta(days=1), user.locale.value),
    )
    return 1


async def _month_milestones(
    uow: CoachingUoW,
    clock: Clock,
    texts: ChallengeTexts,
    user_id: UUID,
    mine: list[tuple[Participation, Challenge]],
    today: date,
    locale: str,
) -> int:
    sent = 0
    for participation, challenge in mine:
        elapsed = (today - participation.start_date).days
        roadmap = texts.roadmap(challenge, locale)
        if roadmap is None or elapsed <= 0 or elapsed % DAYS_PER_MONTH:
            continue
        month = elapsed // DAYS_PER_MONTH + 1
        if month > len(roadmap.months):
            continue
        await _notify(
            uow,
            clock,
            key=f"month:{participation.id}:{month}",
            user_id=user_id,
            participation_id=participation.id,
            moment=Moment.MONTH_STARTED,
            title=texts.title(challenge, locale),
            month=month,
            done_goal=roadmap.months[month - 2],
            goal=roadmap.months[month - 1],
        )
        sent += 1
    return sent


async def send_task_reminders(
    cmd: SendTaskReminders, uow: CoachingUoW, *, clock: Clock, texts: ChallengeTexts = _OWN_TEXTS
) -> int:
    """For each task with a clock time that has just come and has no proof yet."""
    sent = 0
    async with uow:
        for participation_id in await uow.participations.list_open_ids():
            participation = await uow.participations.get(participation_id)
            if participation is None or participation.status is not ParticipationStatus.ACTIVE:
                continue
            user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
            now = clock.now().astimezone(ZoneInfo(user.timezone))
            today = now.date()
            if participation.days.get(today) is not DayStatus.PENDING:
                continue
            due = [
                t
                for t in participation.tasks_on(today)
                if t.at is not None
                and timedelta(0)
                <= now.replace(tzinfo=None) - datetime.combine(today, t.at)
                < REMINDER_WINDOW
            ]
            if not due:
                continue
            proofs = await uow.proofs.list_for_day(participation_id, today)
            handled = {p.task_key for p in proofs if p.status is not ProofStatus.REJECTED}
            challenge = require(
                await uow.challenges.get(participation.challenge_id), "Challenge topilmadi"
            )
            locale = user.locale.value
            for task in due:
                if task.key in handled:
                    continue
                await _notify(
                    uow,
                    clock,
                    key=f"due:{participation_id}:{today.isoformat()}:{task.key}",
                    user_id=user.id,
                    participation_id=participation_id,
                    moment=Moment.TASK_DUE,
                    name=user.username,
                    task=texts.task_title(challenge, task, locale),
                    at=task.at.strftime("%H:%M") if task.at else "",
                    minutes=task.minutes,
                    focus=_focus_text(texts, challenge, participation, today, locale),
                )
                sent += 1
        sent += await _routine_moments(uow, clock, texts)
        await uow.commit()
    return sent


async def mark_read(cmd: MarkNotificationsRead, uow: CoachingUoW, *, clock: Clock) -> None:
    async with uow:
        for notification_id in cmd.notification_ids:
            notification = await uow.notifications.get(notification_id)
            if notification is not None and notification.user_id == cmd.user_id:
                notification.mark_read(clock.now())
        await uow.commit()


async def forget_notifications(event: AccountErased, uow: CoachingUoW) -> None:
    async with uow:
        await uow.notifications.delete_for_user(event.user_id)
        await uow.commit()


# --- weekly summary and cheers ---------------------------------------------------------------

CHEER_EMOJIS = ("👏", "🔥", "💪", "❤️")


async def _group_rank(uow: CoachingUoW, participation: Participation) -> int | None:
    """1-based place in the group (most days done, then the longest streak); None if alone."""
    if participation.group_id is None:
        return None
    members = []
    for member_id in await uow.participations.list_in_group(participation.group_id):
        member = await uow.participations.get(member_id)
        if member is not None and member.status is not ParticipationStatus.CANCELLED:
            members.append(member)
    if len(members) < 2:
        return None
    members.sort(key=lambda m: (m.days_completed, m.current_streak), reverse=True)
    return next(i for i, m in enumerate(members, 1) if m.id == participation.id)


async def send_weekly_summaries(cmd: SendWeeklySummaries, uow: CoachingUoW, *, clock: Clock) -> int:
    sent = 0
    async with uow:
        runs_by_user: dict[UUID, list[Participation]] = {}
        for participation_id in await uow.participations.list_open_ids():
            run = await uow.participations.get(participation_id)
            if run is not None and run.status is ParticipationStatus.ACTIVE:
                runs_by_user.setdefault(run.user_id, []).append(run)
        for user_id, runs in runs_by_user.items():
            user = await uow.users.get(user_id)
            if user is None or user.is_erased:
                continue
            today = local_date(clock.now(), user.timezone)
            monday = today - timedelta(days=today.weekday())
            week = [(d, s) for run in runs for d, s in run.days.items() if monday <= d <= today]
            if not week:
                continue  # a rest week: nothing to sum up
            done = sum(1 for _, status in week if status is DayStatus.DONE)
            ratio = done / len(week)
            moment = (
                Moment.WEEKLY_GREAT
                if ratio >= 0.8
                else Moment.WEEKLY_OK
                if ratio >= 0.5
                else Moment.WEEKLY_TOUGH
            )
            grouped = next((run for run in runs if run.group_id), None)
            rank = await _group_rank(uow, grouped) if grouped else None
            await _notify(
                uow,
                clock,
                key=f"weekly:{user_id}:{monday.isoformat()}",
                user_id=user_id,
                moment=moment,
                participation_id=(grouped or runs[0]).id,
                name=user.username,
                done=done,
                planned=len(week),
                streak=max(run.current_streak for run in runs),
                rank=rank or "",
            )
            sent += 1
        await uow.commit()
    return sent


async def cheer_friend(cmd: CheerFriend, uow: CoachingUoW, *, clock: Clock) -> None:
    """Idempotent per day and pair: a second cheer the same day changes nothing."""
    async with uow:
        mine = require(await uow.participations.get(cmd.participation_id), "Challenge topilmadi")
        if mine.user_id != cmd.user_id:
            raise PermissionDenied("Bu sizning challenge'ingiz emas")
        if mine.group_id is None:
            raise DomainError("Bu challenge guruhda emas")
        sender = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        friend = require(
            await uow.users.get_by_username(cmd.friend_username.strip().lower()),
            "Foydalanuvchi topilmadi",
        )
        mates = await _group_mates(uow, mine.group_id, cmd.user_id)
        target = next((m for m in mates if m.user_id == friend.id), None)
        if target is None:
            raise DomainError("Bu foydalanuvchi guruhingizda emas")
        emoji = cmd.emoji if cmd.emoji in CHEER_EMOJIS else CHEER_EMOJIS[0]
        today = local_date(clock.now(), friend.timezone)
        await _notify(
            uow,
            clock,
            key=f"cheer:{sender.id}:{friend.id}:{today.isoformat()}",
            user_id=friend.id,
            moment=Moment.CHEER,
            participation_id=target.id,
            subject_id=sender.id,
            friend=sender.username,
            emoji=emoji,
        )
        await uow.commit()
