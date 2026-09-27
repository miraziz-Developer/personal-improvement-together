"""Life plan: several goals in one hourly routine, and the day's timeline to live by."""

from datetime import time
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from pit.api import schemas as s
from pit.api import views
from pit.api.deps import ContainerDep, LocaleDep, UserId
from pit.api.ratelimit import rate_limit
from pit.catalog_ru import catalog_text
from pit.modules.challenges.domain.participation import ParticipationStatus
from pit.modules.challenges.infrastructure.tables import participations
from pit.modules.planning.application.commands import (
    DraftLifePlan,
    EditLifePlanGoal,
    StartLifePlan,
)
from pit.modules.planning.domain.life_plan import GoalAnswers, LifePlan, LifePlanRequest
from pit.modules.planning.domain.routine import BusyBlock, DayFrame, minutes_of
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied

router = APIRouter(tags=["life-plans"])

Clock = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class GoalIn(BaseModel):
    goal: str
    motivation: str = ""
    current_level: str = ""


class BusyIO(BaseModel):
    label: str
    weekdays: list[int]
    start: Clock
    end: Clock


class LifePlanIn(BaseModel):
    goals: list[GoalIn]
    wake: Clock
    sleep: Clock
    busy: list[BusyIO] = []
    duration_days: int


class LifeGoalOut(BaseModel):
    key: str
    goal: str
    title: str
    description: str
    category: str
    difficulty: int
    verification_prompt: str
    week: s.Week
    roadmap: s.RoadmapOut | None
    participation_id: UUID | None


class LifePlanOut(BaseModel):
    id: UUID
    status: str
    duration_days: int
    wake: str
    sleep: str
    busy: list[BusyIO]
    budgets: list[int]  # 80% of the free minutes per weekday, Monday first
    goals: list[LifeGoalOut]


class RoutineItem(BaseModel):
    kind: Literal["wake", "busy", "task", "sleep"]
    start: str
    end: str | None = None
    title: str
    participation_id: UUID | None = None
    challenge_title: str | None = None
    category: str | None = None
    task: s.TaskTodayOut | None = None
    lesson: str | None = None


class MonthGoal(BaseModel):
    participation_id: UUID
    title: str
    month: int
    goal: str


class RoutineOut(BaseModel):
    date: str
    has_life_plan: bool
    items: list[RoutineItem]  # the timeline, earliest first
    untimed: list[RoutineItem]  # today's tasks without a clock time
    months: list[MonthGoal]


def _hhmm(moment: time) -> str:
    return moment.strftime("%H:%M")


def _frame(body: LifePlanIn) -> DayFrame:
    return DayFrame(
        wake=time.fromisoformat(body.wake),
        sleep=time.fromisoformat(body.sleep),
        busy=tuple(
            BusyBlock(
                label=b.label.strip(),
                weekdays=frozenset(b.weekdays),
                start=time.fromisoformat(b.start),
                end=time.fromisoformat(b.end),
            )
            for b in body.busy
        ),
    )


def life_plan_out(plan: LifePlan) -> LifePlanOut:
    frame = plan.frame
    return LifePlanOut(
        id=plan.id,
        status=plan.status.value,
        duration_days=plan.duration_days,
        wake=_hhmm(frame.wake),
        sleep=_hhmm(frame.sleep),
        busy=[
            BusyIO(
                label=b.label, weekdays=sorted(b.weekdays), start=_hhmm(b.start), end=_hhmm(b.end)
            )
            for b in frame.busy
        ],
        budgets=[frame.budget(d) for d in range(7)],
        goals=[
            LifeGoalOut(
                key=g.key,
                goal=g.answers.goal,
                title=g.proposal.title,
                description=g.proposal.description,
                category=g.proposal.category.value,
                difficulty=g.proposal.difficulty,
                verification_prompt=g.proposal.verification_prompt,
                week=s.schedule_to_week(g.proposal.schedule),
                roadmap=s.RoadmapOut.of(g.proposal.roadmap),
                participation_id=g.participation_id,
            )
            for g in plan.goals
        ],
    )


async def _load(plan_id: UUID, user_id: UUID, container: ContainerDep) -> LifePlanOut:
    async with container.uow_factory() as uow:
        plan = require(await uow.life_plans.get(plan_id), "Reja topilmadi")
        if plan.user_id != user_id:
            raise PermissionDenied("Bu sizning rejangiz emas")
        return life_plan_out(plan)


@router.post(
    "/life-plans",
    response_model=LifePlanOut,
    status_code=201,
    dependencies=[Depends(rate_limit("life-plans", 5, 3600, per="user"))],  # several AI calls
)
async def draft(
    body: LifePlanIn, user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> LifePlanOut:
    request = LifePlanRequest(
        goals=tuple(
            GoalAnswers(goal=g.goal, motivation=g.motivation, current_level=g.current_level)
            for g in body.goals
        ),
        frame=_frame(body),
        duration_days=body.duration_days,
        language=locale.value,
    )
    plan_id = await container.bus.handle(DraftLifePlan(user_id=user_id, request=request))
    return await _load(plan_id, user_id, container)


@router.get("/life-plans/{plan_id}", response_model=LifePlanOut)
async def get_life_plan(plan_id: UUID, user_id: UserId, container: ContainerDep) -> LifePlanOut:
    return await _load(plan_id, user_id, container)


@router.put("/life-plans/{plan_id}/goals/{goal_key}", response_model=LifePlanOut)
async def edit_goal(
    plan_id: UUID, goal_key: str, body: s.ScheduleIn, user_id: UserId, container: ContainerDep
) -> LifePlanOut:
    await container.bus.handle(
        EditLifePlanGoal(
            user_id=user_id,
            plan_id=plan_id,
            goal_key=goal_key,
            schedule=s.week_to_schedule(body.week),
        )
    )
    return await _load(plan_id, user_id, container)


@router.post("/life-plans/{plan_id}/start", response_model=LifePlanOut)
async def start(plan_id: UUID, user_id: UserId, container: ContainerDep) -> LifePlanOut:
    await container.bus.handle(StartLifePlan(user_id=user_id, plan_id=plan_id))
    return await _load(plan_id, user_id, container)


@router.get("/me/life-plan", response_model=LifePlanOut | None)
async def my_life_plan(user_id: UserId, container: ContainerDep) -> LifePlanOut | None:
    async with container.uow_factory() as uow:
        plan = await uow.life_plans.latest_started(user_id)
        return life_plan_out(plan) if plan else None


@router.get("/me/routine", response_model=RoutineOut)
async def my_routine(user_id: UserId, container: ContainerDep, locale: LocaleDep) -> RoutineOut:
    """Today as one timeline: waking up, fixed commitments, every goal's tasks, sleep."""
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        today = local_date(container.clock.now(), user.timezone)
        plan = await uow.life_plans.latest_started(user_id)
        items: list[RoutineItem] = []
        untimed: list[RoutineItem] = []
        months: list[MonthGoal] = []
        if plan is not None:
            frame = plan.frame
            items.append(RoutineItem(kind="wake", start=_hhmm(frame.wake), title="wake"))
            items.append(RoutineItem(kind="sleep", start=_hhmm(frame.sleep), title="sleep"))
            items.extend(
                RoutineItem(kind="busy", start=_hhmm(b.start), end=_hhmm(b.end), title=b.label)
                for b in frame.busy_on(today.weekday())
            )
        ids = await uow.session.execute(
            select(participations.c.id).where(
                participations.c.user_id == user_id,
                participations.c.status == ParticipationStatus.ACTIVE.value,
            )
        )
        secret = container.settings.daily_code_secret.get_secret_value().encode()
        for participation_id in ids.scalars():
            p = require(await uow.participations.get(participation_id), "Challenge topilmadi")
            challenge = require(await uow.challenges.get(p.challenge_id), "Challenge topilmadi")
            text = catalog_text(challenge.id, locale)
            roadmap = views.roadmap_of(challenge, text)
            proofs = await uow.proofs.list_for_day(p.id, today)
            today_view = views.today_out(p, proofs, today, secret, text, roadmap)
            title = text.title if text else challenge.title
            focus = today_view.focus
            if focus is not None and focus.month_goal:
                months.append(
                    MonthGoal(
                        participation_id=p.id, title=title, month=focus.month, goal=focus.month_goal
                    )
                )
            for task in today_view.tasks:
                item = RoutineItem(
                    kind="task",
                    start=task.at or "",
                    end=None,
                    title=task.title,
                    participation_id=p.id,
                    challenge_title=title,
                    category=challenge.category.value,
                    task=task,
                    lesson=focus.lesson if focus else None,
                )
                if task.at:
                    end = minutes_of(time.fromisoformat(task.at)) + task.minutes
                    item.end = f"{min(end, 1439) // 60:02d}:{min(end, 1439) % 60:02d}"
                    items.append(item)
                else:
                    untimed.append(item)
    order = {"wake": 0, "busy": 1, "task": 2, "sleep": 3}
    items.sort(key=lambda i: (i.start, order[i.kind]))
    return RoutineOut(
        date=today.isoformat(),
        has_life_plan=plan is not None,
        items=items,
        untimed=untimed,
        months=months,
    )
