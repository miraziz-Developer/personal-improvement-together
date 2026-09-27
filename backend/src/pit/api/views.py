"""Read side: turns aggregates and plain SQL into response models. Never writes."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select

from pit.api import schemas as s
from pit.catalog_ru import CatalogText, catalog_text
from pit.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.challenges.domain.participation import (
    OPEN_STATUSES,
    Participation,
    ParticipationStatus,
)
from pit.modules.challenges.domain.roadmap import Roadmap
from pit.modules.challenges.infrastructure.tables import participations
from pit.modules.coaching.infrastructure.tables import notifications
from pit.modules.identity.domain.user import Locale
from pit.modules.identity.infrastructure.tables import regions
from pit.modules.ranking.infrastructure.tables import score_entries
from pit.modules.verification.domain.daily_code import daily_code
from pit.modules.verification.domain.proof import Proof
from pit.shared.application.lookup import require


async def participant_counts(uow: SqlAlchemyUnitOfWork) -> dict[UUID, int]:
    rows = await uow.session.execute(
        select(participations.c.challenge_id, func.count()).group_by(participations.c.challenge_id)
    )
    return {challenge_id: count for challenge_id, count in rows.tuples()}


def localized_week(week: s.Week, text: CatalogText | None) -> s.Week:
    if text is None:
        return week
    return [
        [task.model_copy(update={"title": text.tasks.get(task.key, task.title)}) for task in day]
        for day in week
    ]


def roadmap_of(challenge: Challenge, text: CatalogText | None) -> Roadmap | None:
    return text.roadmap if text and text.roadmap else challenge.roadmap


def challenge_out(
    challenge: Challenge, participants: int, locale: Locale = Locale.UZ
) -> s.ChallengeOut:
    schedule = challenge.default_schedule
    text = catalog_text(challenge.id, locale)
    return s.ChallengeOut(
        id=challenge.id,
        title=text.title if text else challenge.title,
        description=text.description if text else challenge.description,
        category=challenge.category.value,
        duration_days=challenge.duration_days,
        difficulty=challenge.difficulty,
        proof_types=sorted(p.value for p in challenge.proof_types),
        stake_allowed=challenge.stake_policy.allowed,
        min_stake=challenge.stake_policy.min_stake.amount,
        max_stake=challenge.stake_policy.max_stake.amount,
        days_per_week=schedule.active_days_per_week,
        minutes_per_week=schedule.required_minutes_per_week,
        participants=participants,
        week=localized_week(s.schedule_to_week(schedule), text),
        roadmap=s.RoadmapOut.of(roadmap_of(challenge, text)),
    )


def participation_out(
    p: Participation, challenge: Challenge, today: date, locale: Locale = Locale.UZ
) -> s.ParticipationOut:
    text = catalog_text(challenge.id, locale)
    return s.ParticipationOut(
        id=p.id,
        challenge_id=challenge.id,
        title=text.title if text else challenge.title,
        category=challenge.category.value,
        status=p.status.value,
        mode=p.mode.value,
        stake=p.stake.amount,
        start_date=p.start_date,
        end_date=p.end_date,
        days_completed=p.days_completed,
        total_days=len(p.days),
        current_streak=p.current_streak,
        best_streak=p.best_streak,
        freezes_left=p.freezes_left,
        today_status=p.days[today].value if today in p.days else None,
    )


def today_out(
    p: Participation,
    proofs: list[Proof],
    today: date,
    secret: bytes,
    text: CatalogText | None = None,
    roadmap: Roadmap | None = None,
) -> s.TodayOut:
    latest: dict[str, Proof] = {}
    for proof in sorted(proofs, key=lambda x: x.submitted_at):
        latest[proof.task_key] = proof
    tasks = [
        s.TaskTodayOut(
            key=t.key,
            title=text.tasks.get(t.key, t.title) if text else t.title,
            minutes=t.minutes,
            required=t.required,
            at=t.at.strftime("%H:%M") if t.at else None,
            proof_status=latest[t.key].status.value if t.key in latest else None,
            reason=(
                latest[t.key].ai_verdict.reason  # type: ignore[union-attr]
                if t.key in latest and latest[t.key].ai_verdict
                else None
            ),
        )
        for t in p.tasks_on(today)
    ]
    show_code = p.is_stake and p.status is ParticipationStatus.ACTIVE and today in p.days
    return s.TodayOut(
        date=today,
        is_rest_day=today not in p.days,
        status=p.days[today].value if today in p.days else None,
        tasks=tasks,
        daily_code=daily_code(secret, p.id, today) if show_code else None,
        focus=s.FocusOut.of(roadmap.focus(p.start_date, p.days, today) if roadmap else None),
    )


async def participation_detail(
    uow: SqlAlchemyUnitOfWork,
    p: Participation,
    today: date,
    secret: bytes,
    locale: Locale = Locale.UZ,
) -> s.ParticipationDetailOut:
    challenge = require(await uow.challenges.get(p.challenge_id), "Challenge topilmadi")
    proofs = await uow.proofs.list_for_day(p.id, today)
    summary = participation_out(p, challenge, today, locale)
    text = catalog_text(challenge.id, locale)
    return s.ParticipationDetailOut(
        **summary.model_dump(),
        calendar=[s.DayOut(date=d, status=st.value) for d, st in sorted(p.days.items())],
        today=today_out(p, proofs, today, secret, text, roadmap_of(challenge, text)),
        week=localized_week(s.schedule_to_week(p.current_schedule), text),
        can_cancel=p.status is ParticipationStatus.SCHEDULED and today < p.start_date,
        roadmap=s.RoadmapOut.of(roadmap_of(challenge, text)),
    )


async def region_name(
    uow: SqlAlchemyUnitOfWork, region_id: UUID, locale: Locale = Locale.UZ
) -> str:
    column = regions.c.name_ru if locale is Locale.RU else regions.c.name_uz
    row = await uow.session.execute(select(column).where(regions.c.id == region_id))
    return str(row.scalar_one_or_none() or "")


async def user_stats(uow: SqlAlchemyUnitOfWork, user_id: UUID) -> tuple[int, int, int, int, int]:
    """(points, active, completed, best streak, unread notifications)"""
    session = uow.session
    points = (
        await session.execute(
            select(func.coalesce(func.sum(score_entries.c.points), 0)).where(
                score_entries.c.user_id == user_id
            )
        )
    ).scalar_one()
    open_values = [st.value for st in OPEN_STATUSES]
    counts = (
        await session.execute(
            select(
                func.count().filter(participations.c.status.in_(open_values)),
                func.count().filter(participations.c.status == ParticipationStatus.COMPLETED.value),
                func.coalesce(func.max(participations.c.best_streak), 0),
            ).where(participations.c.user_id == user_id)
        )
    ).one()
    unread = (
        await session.execute(
            select(func.count()).where(
                notifications.c.user_id == user_id, notifications.c.read_at.is_(None)
            )
        )
    ).scalar_one()
    return int(points), int(counts[0]), int(counts[1]), int(counts[2]), int(unread)
