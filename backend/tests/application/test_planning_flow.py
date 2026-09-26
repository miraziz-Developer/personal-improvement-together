"""Register -> onboarding -> AI plan -> (edit) -> start -> daily tasks."""

from uuid import UUID

import pytest

from pit.modules.challenges.application.commands import ChangeSchedule
from pit.modules.challenges.domain.challenge import Category, ParticipationMode
from pit.modules.challenges.domain.participation import DayStatus, ParticipationStatus
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.identity.domain.user import User
from pit.modules.planning.application.commands import DraftPlan, EditPlan, StartPlan
from pit.modules.planning.domain.plan import PlanProposal, PlanStatus
from pit.shared.domain.errors import DomainError
from pit.shared.domain.money import Money
from tests.application.conftest import World
from tests.factories import ANSWERS

LESSON = TaskSpec(key="lesson", title="FastAPI darsi", minutes=45)
PRACTICE = TaskSpec(key="practice", title="1 ta endpoint yozish", minutes=30)
EXTRA = TaskSpec(key="extra", title="Qo'shimcha maqola o'qish", minutes=20, required=False)
PROJECT = TaskSpec(key="project", title="Shaxsiy loyiha", minutes=150)

# Mon-Fri: lesson + practice (+ optional extra) = 95 min <= 96; Sat: project; Sun: rest.
WEEK = Schedule.by_weekday({**{d: [LESSON, PRACTICE, EXTRA] for d in range(5)}, 5: [PROJECT]})


def proposal(schedule: Schedule = WEEK) -> PlanProposal:
    return PlanProposal(
        title="Backend: 1-bosqich",
        description="FastAPI asoslari",
        category=Category.CODE,
        duration_days=14,
        difficulty=3,
        verification_prompt="Kod, terminal yoki dars konspekti ko'rinishi kerak",
        schedule=schedule,
    )


async def start_plan(
    world: World, user: User, *, schedule: Schedule = WEEK, stake: int = 0
) -> UUID:
    world.planner.next_proposal = proposal(schedule)
    plan_id: UUID = await world.bus.handle(DraftPlan(user_id=user.id, answers=ANSWERS))
    mode = ParticipationMode.STAKE if stake else ParticipationMode.FREE
    participation_id: UUID = await world.bus.handle(
        StartPlan(user_id=user.id, plan_id=plan_id, mode=mode, stake_amount=stake)
    )
    return participation_id


async def test_onboarding_answers_become_a_personal_stake_challenge(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    world.planner.next_proposal = proposal()

    plan_id = await world.bus.handle(DraftPlan(user_id=user.id, answers=ANSWERS))
    lighter_saturday = Schedule.by_weekday(
        {**{d: [LESSON, PRACTICE] for d in range(5)}, 5: [LESSON]}
    )
    await world.bus.handle(EditPlan(user_id=user.id, plan_id=plan_id, schedule=lighter_saturday))
    pid = await world.bus.handle(
        StartPlan(
            user_id=user.id, plan_id=plan_id, mode=ParticipationMode.STAKE, stake_amount=100_000
        )
    )

    assert world.planner.asked == [ANSWERS]
    assert world.store.plans[plan_id].status is PlanStatus.STARTED
    participation = world.participation(pid)
    assert participation.current_schedule == lighter_saturday
    assert world.store.challenges[participation.challenge_id].created_by == user.id
    assert world.wallet(user).locked == Money(100_000)


async def test_a_day_counts_only_when_every_required_task_is_approved(world: World) -> None:
    user = world.add_user()
    pid = await start_plan(world, user)  # starts on a Thursday
    today = world.today

    await world.prove(user, pid, task="lesson", photo=False)
    assert world.participation(pid).days[today] is DayStatus.PENDING

    await world.prove(user, pid, task="practice", photo=False)
    assert world.participation(pid).days[today] is DayStatus.DONE


async def test_missing_one_required_task_misses_the_day(world: World) -> None:
    user = world.add_user()
    pid = await start_plan(world, user)  # 12 scheduled days -> 1 freeze
    today = world.today

    await world.prove(user, pid, task="lesson", photo=False)
    await world.next_day()

    participation = world.participation(pid)
    assert participation.days[today] is DayStatus.FROZEN
    assert participation.freezes_left == 0


async def test_optional_task_earns_points_but_never_decides_the_day(world: World) -> None:
    user = world.add_user()
    pid = await start_plan(world, user)
    today = world.today

    await world.prove(user, pid, task="extra", photo=False)

    assert world.participation(pid).days[today] is DayStatus.PENDING
    assert world.leaderboard.boards["lb:all:global"][user.id] == 2  # 20 min -> 2 points


async def test_rest_day_is_never_missed(world: World) -> None:
    user = world.add_user()
    monday_only = Schedule.by_weekday({0: [LESSON]})
    pid = await start_plan(world, user, schedule=monday_only)  # Thursday: rest day

    with pytest.raises(DomainError, match="dam olish"):
        await world.submit(user, pid, task="lesson", photo=False)
    await world.next_day()  # Thursday closes with no proof — nothing happens

    participation = world.participation(pid)
    assert participation.status is ParticipationStatus.ACTIVE
    assert participation.freezes_used == 0


async def test_stake_plan_can_only_get_harder(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await start_plan(world, user, stake=100_000)

    three_days = Schedule.by_weekday({d: [LESSON, PRACTICE] for d in (0, 2, 4)})
    with pytest.raises(DomainError, match="qiyinlashtirish"):
        await world.bus.handle(
            ChangeSchedule(user_id=user.id, participation_id=pid, schedule=three_days)
        )

    every_day = Schedule.every_day(LESSON, PRACTICE, PROJECT)
    await world.bus.handle(
        ChangeSchedule(user_id=user.id, participation_id=pid, schedule=every_day)
    )
    assert world.participation(pid).current_schedule == every_day


async def test_ai_plan_that_overloads_free_time_is_refused(world: World) -> None:
    user = world.add_user()
    world.planner.next_proposal = proposal(Schedule.every_day(PROJECT))  # 150 min on weekdays

    with pytest.raises(DomainError, match="80%"):
        await world.bus.handle(DraftPlan(user_id=user.id, answers=ANSWERS))
    assert world.store.plans == {}


async def test_stake_on_a_too_light_plan_freezes_nothing(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)

    with pytest.raises(DomainError, match="Pulli rejim uchun"):
        await start_plan(world, user, schedule=Schedule.by_weekday({0: [LESSON]}), stake=50_000)

    assert world.wallet(user).locked == Money.zero()
    assert world.store.participations == {}
