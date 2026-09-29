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
from pit.modules.challenges.infrastructure.tables import challenges, participations
from pit.modules.identity.domain.user import Locale
from pit.modules.planning.application.commands import (
    AddToRoutine,
    ChangeDayFrame,
    DraftLifePlan,
    EditLifePlanGoal,
    RetimeLifePlanRun,
    RetimeTasks,
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


class RunTimesIn(BaseModel):
    """When the user does the tasks of a challenge they are already on (same time every day)."""

    participation_id: UUID
    times: dict[str, Clock | None]  # task key -> "HH:MM", None = find a time for me


class FrameIO(BaseModel):
    wake: Clock
    sleep: Clock
    busy: list[BusyIO] = []


class TimesIn(BaseModel):
    times: dict[str, Clock | None]  # task key -> "HH:MM", None = no time


class AddToRoutineIn(BaseModel):
    challenge_id: UUID
    times: dict[str, Clock | None] = {}  # task key -> "HH:MM"; missing/None = find a time


class LifePlanIn(BaseModel):
    goals: list[GoalIn]
    wake: Clock
    sleep: Clock
    busy: list[BusyIO] = []
    duration_days: int
    runs: list[RunTimesIn] = []


class RunOut(BaseModel):
    participation_id: UUID
    title: str
    category: str
    week: s.Week


class CandidateTask(BaseModel):
    key: str
    title: str
    minutes: int
    required: bool
    at: str | None
    weekdays: list[int]  # days of the week the task happens on, 0 = Monday


class CandidateOut(BaseModel):
    """A running challenge the new routine will include."""

    participation_id: UUID
    title: str
    category: str
    tasks: list[CandidateTask]


class CreatedOut(BaseModel):
    """A challenge the user made (AI plan or daily routine goal) and how it is going."""

    challenge: s.ChallengeOut
    participation_id: UUID | None
    status: str | None
    invite_code: str | None
    members: int


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
    runs: list[RunOut]  # challenges already running, with their tasks' times in the routine


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
    frame: FrameIO | None  # the whole day frame, for editing
    items: list[RoutineItem]  # the timeline, earliest first
    untimed: list[RoutineItem]  # today's tasks without a clock time
    months: list[MonthGoal]


def _hhmm(moment: time) -> str:
    return moment.strftime("%H:%M")


def _frame(body: LifePlanIn | FrameIO) -> DayFrame:
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


def _frame_out(frame: DayFrame) -> FrameIO:
    return FrameIO(
        wake=_hhmm(frame.wake),
        sleep=_hhmm(frame.sleep),
        busy=[
            BusyIO(
                label=b.label, weekdays=sorted(b.weekdays), start=_hhmm(b.start), end=_hhmm(b.end)
            )
            for b in frame.busy
        ],
    )


def life_plan_out(plan: LifePlan, locale: Locale = Locale.UZ) -> LifePlanOut:
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
        runs=[
            RunOut(
                participation_id=run.participation_id,
                title=_title(run.challenge_id, run.title, locale),
                category=run.category.value,
                week=views.localized_week(
                    s.schedule_to_week(run.schedule), catalog_text(run.challenge_id, locale)
                ),
            )
            for run in plan.existing
        ],
    )


def _title(challenge_id: UUID, stored: str, locale: Locale) -> str:
    text = catalog_text(challenge_id, locale)
    return text.title if text else stored


async def _load(
    plan_id: UUID, user_id: UUID, container: ContainerDep, locale: Locale = Locale.UZ
) -> LifePlanOut:
    async with container.uow_factory() as uow:
        plan = require(await uow.life_plans.get(plan_id), "Reja topilmadi")
        if plan.user_id != user_id:
            raise PermissionDenied("Bu sizning rejangiz emas")
        return life_plan_out(plan, locale)


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
    times = {
        run.participation_id: {
            key: time.fromisoformat(at) if at else None for key, at in run.times.items()
        }
        for run in body.runs
    }
    plan_id = await container.bus.handle(
        DraftLifePlan(user_id=user_id, request=request, times=times)
    )
    return await _load(plan_id, user_id, container, locale)


@router.get("/life-plans/{plan_id}", response_model=LifePlanOut)
async def get_life_plan(
    plan_id: UUID, user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> LifePlanOut:
    return await _load(plan_id, user_id, container, locale)


@router.put("/life-plans/{plan_id}/runs/{participation_id}", response_model=LifePlanOut)
async def retime_run(
    plan_id: UUID,
    participation_id: UUID,
    body: s.ScheduleIn,
    user_id: UserId,
    container: ContainerDep,
    locale: LocaleDep,
) -> LifePlanOut:
    await container.bus.handle(
        RetimeLifePlanRun(
            user_id=user_id,
            plan_id=plan_id,
            participation_id=participation_id,
            schedule=s.week_to_schedule(body.week),
        )
    )
    return await _load(plan_id, user_id, container, locale)


@router.put("/me/participations/{participation_id}/times", status_code=204)
async def retime_tasks(
    participation_id: UUID, body: TimesIn, user_id: UserId, container: ContainerDep
) -> None:
    """Move tasks on the daily timeline by hand (same time on every day of the task)."""
    await container.bus.handle(
        RetimeTasks(
            user_id=user_id,
            participation_id=participation_id,
            times={k: time.fromisoformat(v) if v else None for k, v in body.times.items()},
        )
    )


@router.post("/me/routine/challenges", response_model=s.IdOut, status_code=201)
async def add_to_routine(body: AddToRoutineIn, user_id: UserId, container: ContainerDep) -> s.IdOut:
    """Join a challenge straight into the daily routine at the chosen times."""
    participation_id = await container.bus.handle(
        AddToRoutine(
            user_id=user_id,
            challenge_id=body.challenge_id,
            times={k: time.fromisoformat(v) if v else None for k, v in body.times.items()},
        )
    )
    return s.IdOut(id=participation_id)


@router.put("/me/life-plan/frame", response_model=LifePlanOut)
async def change_frame(
    body: FrameIO, user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> LifePlanOut:
    await container.bus.handle(ChangeDayFrame(user_id=user_id, frame=_frame(body)))
    async with container.uow_factory() as uow:
        plan = require(await uow.life_plans.latest_started(user_id), "Reja topilmadi")
        return life_plan_out(plan, locale)


@router.get("/me/routine/candidates", response_model=list[CandidateOut])
async def routine_candidates(
    user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> list[CandidateOut]:
    """The challenges a new daily routine will include, task by task."""
    result = []
    async with container.uow_factory() as uow:
        for participation_id in await uow.participations.list_open_ids(user_id):
            p = require(await uow.participations.get(participation_id), "Challenge topilmadi")
            challenge = require(await uow.challenges.get(p.challenge_id), "Challenge topilmadi")
            text = catalog_text(challenge.id, locale)
            tasks: dict[str, CandidateTask] = {}
            for weekday, day in enumerate(p.current_schedule.week):
                for task in day:
                    found = tasks.get(task.key)
                    if found is None:
                        tasks[task.key] = CandidateTask(
                            key=task.key,
                            title=text.tasks.get(task.key, task.title) if text else task.title,
                            minutes=task.minutes,
                            required=task.required,
                            at=task.at.strftime("%H:%M") if task.at else None,
                            weekdays=[weekday],
                        )
                    else:
                        found.weekdays.append(weekday)
            result.append(
                CandidateOut(
                    participation_id=p.id,
                    title=_title(challenge.id, challenge.title, locale),
                    category=challenge.category.value,
                    tasks=list(tasks.values()),
                )
            )
    return result


@router.get("/me/created-challenges", response_model=list[CreatedOut])
async def created_challenges(
    user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> list[CreatedOut]:
    """Challenges the user made — to invite friends to them, and to see how each is going."""
    async with container.uow_factory() as uow:
        ids = await uow.session.execute(
            select(challenges.c.id)
            .where(challenges.c.created_by == user_id)
            .order_by(challenges.c.created_at.desc())
        )
        counts = await views.participant_counts(uow)
        result = []
        for challenge_id in ids.scalars():
            challenge = require(await uow.challenges.get(challenge_id), "Challenge topilmadi")
            mine = await uow.session.execute(
                select(participations.c.id)
                .where(
                    participations.c.challenge_id == challenge_id,
                    participations.c.user_id == user_id,
                )
                .order_by(participations.c.created_at.desc())
                .limit(1)
            )
            participation_id = mine.scalar_one_or_none()
            participation = (
                await uow.participations.get(participation_id) if participation_id else None
            )
            group = (
                await uow.groups.get(participation.group_id)
                if participation and participation.group_id
                else None
            )
            result.append(
                CreatedOut(
                    challenge=views.challenge_out(challenge, counts.get(challenge_id, 0), locale),
                    participation_id=participation.id if participation else None,
                    status=participation.status.value if participation else None,
                    invite_code=group.invite_code if group else None,
                    members=len(group.member_ids) if group else 0,
                )
            )
        return result


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
async def start(
    plan_id: UUID, user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> LifePlanOut:
    await container.bus.handle(StartLifePlan(user_id=user_id, plan_id=plan_id))
    return await _load(plan_id, user_id, container, locale)


@router.get("/me/life-plan", response_model=LifePlanOut | None)
async def my_life_plan(
    user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> LifePlanOut | None:
    async with container.uow_factory() as uow:
        plan = await uow.life_plans.latest_started(user_id)
        return life_plan_out(plan, locale) if plan else None


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
    # Going to bed after midnight ("00:30") still closes the day, so sleep always sorts last.
    items.sort(key=lambda i: ("99" if i.kind == "sleep" else i.start, order[i.kind]))
    return RoutineOut(
        date=today.isoformat(),
        has_life_plan=plan is not None,
        frame=_frame_out(plan.frame) if plan else None,
        items=items,
        untimed=untimed,
        months=months,
    )
