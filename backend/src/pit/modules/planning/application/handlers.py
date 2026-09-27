from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.challenges.application.handlers import (
    ChallengesUoW,
    EscrowFactory,
    start_participation,
)
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.identity.domain.events import AccountErased
from pit.modules.planning.application.commands import (
    DraftLifePlan,
    DraftPlan,
    EditLifePlanGoal,
    EditPlan,
    StartLifePlan,
    StartPlan,
)
from pit.modules.planning.application.ports import LifePlanGenerator, PlanGenerator
from pit.modules.planning.domain.life_plan import LifePlan
from pit.modules.planning.domain.plan import Plan
from pit.modules.planning.domain.repositories import LifePlanRepository, PlanRepository
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied
from pit.shared.domain.money import Money


class PlanningUoW(ChallengesUoW, Protocol):
    @property
    def plans(self) -> PlanRepository: ...

    @property
    def life_plans(self) -> LifePlanRepository: ...


async def _owned_plan(uow: PlanningUoW, plan_id: UUID, user_id: UUID) -> Plan:
    plan = require(await uow.plans.get(plan_id), "Reja topilmadi")
    if plan.user_id != user_id:
        raise PermissionDenied("Bu sizning rejangiz emas")
    return plan


async def draft_plan(cmd: DraftPlan, uow: PlanningUoW, *, generator: PlanGenerator) -> UUID:
    async with uow:
        require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        proposal = await generator.propose(cmd.answers)
        plan = Plan.draft(
            plan_id=uuid4(), user_id=cmd.user_id, answers=cmd.answers, proposal=proposal
        )
        uow.plans.add(plan)
        await uow.commit()
        return plan.id


async def edit_plan(cmd: EditPlan, uow: PlanningUoW) -> None:
    async with uow:
        plan = await _owned_plan(uow, cmd.plan_id, cmd.user_id)
        plan.edit_schedule(cmd.schedule)
        await uow.commit()


async def start_plan(
    cmd: StartPlan,
    uow: PlanningUoW,
    *,
    clock: Clock,
    escrow: EscrowFactory,
    stakes_enabled: bool = True,
) -> UUID:
    """Accepted plan → personal challenge → participation (and frozen stake), atomically."""
    async with uow:
        plan = await _owned_plan(uow, cmd.plan_id, cmd.user_id)
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        today = local_date(clock.now(), user.timezone)
        challenge = Challenge.personal(
            challenge_id=uuid4(), created_by=user.id, **plan.challenge_spec()
        )
        uow.challenges.add(challenge)
        participation = await start_participation(
            uow,
            user=user,
            challenge=challenge,
            mode=cmd.mode,
            stake=Money(cmd.stake_amount),
            start_date=cmd.start_date or today,
            today=today,
            schedule=None,
            escrow=escrow,
            stakes_enabled=stakes_enabled,
        )
        plan.mark_started(challenge_id=challenge.id, participation_id=participation.id)
        await uow.commit()
        return participation.id


async def _owned_life_plan(uow: PlanningUoW, plan_id: UUID, user_id: UUID) -> LifePlan:
    plan = require(await uow.life_plans.get(plan_id), "Reja topilmadi")
    if plan.user_id != user_id:
        raise PermissionDenied("Bu sizning rejangiz emas")
    return plan


async def draft_life_plan(
    cmd: DraftLifePlan, uow: PlanningUoW, *, generator: LifePlanGenerator
) -> UUID:
    async with uow:
        require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        proposals = await generator.propose(cmd.request)
        plan = LifePlan.draft(
            plan_id=uuid4(), user_id=cmd.user_id, request=cmd.request, proposals=proposals
        )
        uow.life_plans.add(plan)
        await uow.commit()
        return plan.id


async def edit_life_plan_goal(cmd: EditLifePlanGoal, uow: PlanningUoW) -> None:
    async with uow:
        plan = await _owned_life_plan(uow, cmd.plan_id, cmd.user_id)
        plan.edit_goal_schedule(cmd.goal_key, cmd.schedule)
        await uow.commit()


async def start_life_plan(
    cmd: StartLifePlan,
    uow: PlanningUoW,
    *,
    clock: Clock,
    escrow: EscrowFactory,
    stakes_enabled: bool = True,
) -> list[UUID]:
    """All goals start together or none does: one transaction."""
    async with uow:
        plan = await _owned_life_plan(uow, cmd.plan_id, cmd.user_id)
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        today = local_date(clock.now(), user.timezone)
        started: dict[str, tuple[UUID, UUID]] = {}
        for goal in plan.goals:
            challenge = Challenge.personal(
                challenge_id=uuid4(), created_by=user.id, **plan.challenge_spec(goal.key)
            )
            uow.challenges.add(challenge)
            participation = await start_participation(
                uow,
                user=user,
                challenge=challenge,
                mode=ParticipationMode.FREE,
                stake=Money(0),
                start_date=today,
                today=today,
                schedule=None,
                escrow=escrow,
                stakes_enabled=stakes_enabled,
            )
            started[goal.key] = (challenge.id, participation.id)
        plan.mark_started(started)
        await uow.commit()
        return [participation_id for _, participation_id in started.values()]


async def forget_plans(event: AccountErased, uow: PlanningUoW) -> None:
    """Goals and motivations are personal: they go with the account."""
    async with uow:
        await uow.plans.delete_for_user(event.user_id)
        await uow.life_plans.delete_for_user(event.user_id)
        await uow.commit()
