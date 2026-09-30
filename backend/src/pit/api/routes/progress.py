"""Progress: how the last weeks went, day by day and challenge by challenge."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from pit.api import views
from pit.api.deps import ContainerDep, LocaleDep, UserId
from pit.catalog_ru import catalog_text
from pit.modules.challenges.domain.participation import DayStatus, Participation
from pit.modules.challenges.infrastructure.tables import participations
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require

router = APIRouter(tags=["progress"])

WINDOW_DAYS = 30


class DayOut(BaseModel):
    day: date
    planned: int  # challenges that had this day in their plan (paused days excluded)
    done: int


class RunProgress(BaseModel):
    participation_id: UUID
    title: str
    category: str
    status: str
    days_completed: int
    total_days: int
    current_streak: int
    month: int | None
    month_goal: str | None


class ProgressOut(BaseModel):
    days: list[DayOut]  # oldest first, up to today
    this_week: float | None  # share of planned days done, last 7 days
    last_week: float | None  # the 7 days before that
    days_done: int  # all time
    best_streak: int
    runs: list[RunProgress]  # open challenges


def _share(days: list[DayOut]) -> float | None:
    planned = sum(d.planned for d in days)
    return round(sum(d.done for d in days) / planned, 3) if planned else None


def _counts(runs: list[Participation], day: date) -> tuple[int, int]:
    planned = done = 0
    for run in runs:
        status = run.days.get(day)
        if status is None or status is DayStatus.PAUSED:
            continue
        planned += 1
        done += status is DayStatus.DONE
    return planned, done


@router.get("/me/progress", response_model=ProgressOut)
async def my_progress(user_id: UserId, container: ContainerDep, locale: LocaleDep) -> ProgressOut:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        today = local_date(container.clock.now(), user.timezone)
        ids = await uow.session.execute(
            select(participations.c.id).where(participations.c.user_id == user_id)
        )
        runs = [
            require(await uow.participations.get(pid), "Challenge topilmadi")
            for pid in ids.scalars()
        ]
        # Today is not over yet: it counts only once done, so it never drags the share down.
        days = []
        for offset in range(WINDOW_DAYS - 1, -1, -1):
            day = today - timedelta(days=offset)
            planned, done = _counts(runs, day)
            if day == today and done < planned:
                planned = done
            days.append(DayOut(day=day, planned=planned, done=done))
        open_runs = []
        for run in runs:
            if not run.is_open:
                continue
            challenge = require(await uow.challenges.get(run.challenge_id), "Challenge topilmadi")
            text = catalog_text(challenge.id, locale)
            roadmap = views.roadmap_of(challenge, text)
            focus = roadmap.focus(run.start_date, run.days, today) if roadmap else None
            open_runs.append(
                RunProgress(
                    participation_id=run.id,
                    title=text.title if text else challenge.title,
                    category=challenge.category.value,
                    status=run.status.value,
                    days_completed=run.days_completed,
                    total_days=run.total_days,
                    current_streak=run.current_streak,
                    month=focus.month if focus and focus.month_goal else None,
                    month_goal=focus.month_goal if focus else None,
                )
            )
        return ProgressOut(
            days=days,
            this_week=_share(days[-7:]),
            last_week=_share(days[-14:-7]),
            days_done=sum(run.days_completed for run in runs),
            best_streak=max((run.best_streak for run in runs), default=0),
            runs=open_runs,
        )
