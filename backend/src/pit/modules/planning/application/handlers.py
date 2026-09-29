from collections.abc import Mapping
from dataclasses import replace
from datetime import time
from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.challenges.application.handlers import (
    ChallengesUoW,
    EscrowFactory,
    start_participation,
)
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.identity.domain.events import AccountErased
from pit.modules.planning.application.commands import (
    AddToRoutine,
    ChangeDayFrame,
    DraftLifePlan,
    DraftPlan,
    EditLifePlanGoal,
    EditPlan,
    RetimeLifePlanRun,
    RetimeTasks,
    StartLifePlan,
    StartPlan,
)
from pit.modules.planning.application.ports import LifePlanGenerator, PlanGenerator
from pit.modules.planning.domain.life_plan import ExistingRun, LifePlan
from pit.modules.planning.domain.plan import Plan
from pit.modules.planning.domain.repositories import LifePlanRepository, PlanRepository
from pit.modules.planning.domain.routine import check_clashes, pack
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import NotFound, PermissionDenied
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


async def _running(
    uow: PlanningUoW, user_id: UUID, times: Mapping[UUID, Mapping[str, time | None]]
) -> tuple[ExistingRun, ...]:
    """Every open challenge of the user, with the clock times they picked for its tasks."""
    runs = []
    for participation_id in await uow.participations.list_open_ids(user_id):
        participation = require(
            await uow.participations.get(participation_id), "Challenge topilmadi"
        )
        challenge = require(
            await uow.challenges.get(participation.challenge_id), "Challenge topilmadi"
        )
        chosen = times.get(participation_id, {})
        schedule = participation.current_schedule
        timed = Schedule(
            week=tuple(
                tuple(replace(t, at=chosen[t.key]) if t.key in chosen else t for t in day)
                for day in schedule.week
            )
        )
        runs.append(
            ExistingRun(
                participation_id=participation.id,
                challenge_id=challenge.id,
                title=challenge.title,
                category=challenge.category,
                schedule=timed,
            )
        )
    return tuple(runs)


async def draft_life_plan(
    cmd: DraftLifePlan, uow: PlanningUoW, *, generator: LifePlanGenerator
) -> UUID:
    async with uow:
        require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        request = replace(cmd.request, existing=await _running(uow, cmd.user_id, cmd.times))
        proposals = await generator.propose(request)
        plan = LifePlan.draft(
            plan_id=uuid4(), user_id=cmd.user_id, request=request, proposals=proposals
        )
        uow.life_plans.add(plan)
        await uow.commit()
        return plan.id


async def edit_life_plan_goal(cmd: EditLifePlanGoal, uow: PlanningUoW) -> None:
    async with uow:
        plan = await _owned_life_plan(uow, cmd.plan_id, cmd.user_id)
        plan.edit_goal_schedule(cmd.goal_key, cmd.schedule)
        await uow.commit()


async def retime_life_plan_run(cmd: RetimeLifePlanRun, uow: PlanningUoW) -> None:
    async with uow:
        plan = await _owned_life_plan(uow, cmd.plan_id, cmd.user_id)
        plan.retime_existing(cmd.participation_id, cmd.schedule)
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
        previous = await uow.life_plans.latest_started(user.id)
        if previous is not None and previous.id != plan.id:
            previous.retire()  # one person, one daily routine
        for run in plan.existing:
            participation = await uow.participations.get(run.participation_id)
            if participation is not None and participation.is_open:
                participation.retime(run.schedule, today)
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


async def _running_schedules(
    uow: PlanningUoW, user_id: UUID, besides: UUID | None = None
) -> list[Schedule]:
    schedules = []
    for participation_id in await uow.participations.list_open_ids(user_id):
        if participation_id == besides:
            continue
        participation = await uow.participations.get(participation_id)
        if participation is not None:
            schedules.append(participation.current_schedule)
    return schedules


async def retime_tasks(cmd: RetimeTasks, uow: PlanningUoW, *, clock: Clock) -> None:
    """Hand edits on the daily timeline. Only times change, so it applies from today."""
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        participation = require(
            await uow.participations.get(cmd.participation_id), "Challenge topilmadi"
        )
        if participation.user_id != user.id:
            raise PermissionDenied("Bu sizning challenge'ingiz emas")
        current = participation.current_schedule
        timed = Schedule(
            week=tuple(
                tuple(replace(t, at=cmd.times[t.key]) if t.key in cmd.times else t for t in day)
                for day in current.week
            )
        )
        routine = await uow.life_plans.latest_started(user.id)
        others = await _running_schedules(uow, user.id, besides=participation.id)
        check_clashes(routine.frame if routine else None, [*others, timed])
        participation.retime(timed, local_date(clock.now(), user.timezone))
        await uow.commit()


async def change_day_frame(cmd: ChangeDayFrame, uow: PlanningUoW) -> None:
    async with uow:
        routine = await uow.life_plans.latest_started(cmd.user_id)
        if routine is None:
            raise NotFound("Kun tartibi hali tuzilmagan")
        check_clashes(cmd.frame, await _running_schedules(uow, cmd.user_id))
        routine.change_frame(cmd.frame)
        await uow.commit()


async def add_to_routine(
    cmd: AddToRoutine,
    uow: PlanningUoW,
    *,
    clock: Clock,
    escrow: EscrowFactory,
    stakes_enabled: bool = True,
) -> UUID:
    """The times the user picked are kept as they are; tasks left without one get the first
    free slot of the routine. Nothing is shortened: it is the challenge's own plan."""
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        challenge = require(await uow.challenges.get(cmd.challenge_id), "Challenge topilmadi")
        if not challenge.is_template and challenge.created_by != user.id:
            raise PermissionDenied(
                "Bu shaxsiy challenge — unga faqat taklif havolasi orqali qo'shilish mumkin"
            )
        chosen = {key: at for key, at in cmd.times.items() if at is not None}
        schedule = Schedule(
            week=tuple(
                tuple(replace(t, at=chosen.get(t.key)) for t in day)
                for day in challenge.default_schedule.week
            )
        )
        routine = await uow.life_plans.latest_started(user.id)
        frame = routine.frame if routine else None
        others = await _running_schedules(uow, user.id)
        check_clashes(frame, [*others, schedule])  # the user's own picks must fit as picked
        if frame is not None and any(t.at is None for day in schedule.week for t in day):
            placed = pack(frame, [*others, schedule], fixed=len(others) + 1)[-1]
            schedule = Schedule(
                week=tuple(
                    tuple(replace(t, at=chosen[t.key]) if t.key in chosen else t for t in day)
                    for day in placed.week
                )
            )
            check_clashes(frame, [*others, schedule])
        today = local_date(clock.now(), user.timezone)
        participation = await start_participation(
            uow,
            user=user,
            challenge=challenge,
            mode=ParticipationMode.FREE,
            stake=Money(0),
            start_date=today,
            today=today,
            schedule=schedule,
            escrow=escrow,
            stakes_enabled=stakes_enabled,
        )
        await uow.commit()
        return participation.id
