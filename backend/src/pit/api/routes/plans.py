from uuid import UUID

from fastapi import APIRouter, Depends

from pit.api import schemas as s
from pit.api.deps import ContainerDep, LocaleDep, UserId
from pit.api.ratelimit import rate_limit
from pit.modules.planning.application.commands import DraftPlan, EditPlan, StartPlan
from pit.modules.planning.domain.plan import Availability, OnboardingAnswers, Plan
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied

router = APIRouter(tags=["plans"])


def plan_out(plan: Plan) -> s.PlanOut:
    p = plan.proposal
    return s.PlanOut(
        id=plan.id,
        status=plan.status.value,
        title=p.title,
        description=p.description,
        category=p.category.value,
        duration_days=p.duration_days,
        difficulty=p.difficulty,
        verification_prompt=p.verification_prompt,
        week=s.schedule_to_week(p.schedule),
        budgets=[plan.answers.availability.budget(d) for d in range(7)],
        participation_id=plan.participation_id,
        roadmap=s.RoadmapOut.of(p.roadmap),
    )


async def _load(plan_id: UUID, user_id: UUID, container: ContainerDep) -> s.PlanOut:
    async with container.uow_factory() as uow:
        plan = require(await uow.plans.get(plan_id), "Reja topilmadi")
        if plan.user_id != user_id:
            raise PermissionDenied("Bu sizning rejangiz emas")
        return plan_out(plan)


@router.post(
    "/plans",
    response_model=s.PlanOut,
    status_code=201,
    dependencies=[Depends(rate_limit("plans", 10, 3600, per="user"))],  # AI calls cost money
)
async def draft(
    body: s.AnswersIn, user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> s.PlanOut:
    answers = OnboardingAnswers(
        goal=body.goal,
        motivation=body.motivation,
        current_level=body.current_level,
        obstacles=body.obstacles,
        availability=Availability(minutes_by_weekday=tuple(body.availability)),
        language=locale.value,
    )
    plan_id = await container.bus.handle(DraftPlan(user_id=user_id, answers=answers))
    return await _load(plan_id, user_id, container)


@router.get("/plans/{plan_id}", response_model=s.PlanOut)
async def get_plan(plan_id: UUID, user_id: UserId, container: ContainerDep) -> s.PlanOut:
    return await _load(plan_id, user_id, container)


@router.put("/plans/{plan_id}/schedule", response_model=s.PlanOut)
async def edit(
    plan_id: UUID, body: s.ScheduleIn, user_id: UserId, container: ContainerDep
) -> s.PlanOut:
    await container.bus.handle(
        EditPlan(user_id=user_id, plan_id=plan_id, schedule=s.week_to_schedule(body.week))
    )
    return await _load(plan_id, user_id, container)


@router.post("/plans/{plan_id}/start", response_model=s.IdOut, status_code=201)
async def start(
    plan_id: UUID, body: s.StartIn, user_id: UserId, container: ContainerDep
) -> s.IdOut:
    participation_id = await container.bus.handle(
        StartPlan(
            user_id=user_id,
            plan_id=plan_id,
            mode=body.mode,
            stake_amount=body.stake_amount,
            start_date=body.start_date,
        )
    )
    return s.IdOut(id=participation_id)
