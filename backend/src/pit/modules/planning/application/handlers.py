from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.challenges.application.handlers import (
    ChallengesUoW,
    EscrowFactory,
    start_participation,
)
from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.planning.application.commands import DraftPlan, EditPlan, StartPlan
from pit.modules.planning.application.ports import PlanGenerator
from pit.modules.planning.domain.plan import Plan
from pit.modules.planning.domain.repositories import PlanRepository
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied
from pit.shared.domain.money import Money


class PlanningUoW(ChallengesUoW, Protocol):
    @property
    def plans(self) -> PlanRepository: ...


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
