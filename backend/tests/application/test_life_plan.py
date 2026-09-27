from datetime import time

import pytest

from pit.modules.coaching.application.commands import SendDailyNudges
from pit.modules.coaching.domain.moments import Moment
from pit.modules.identity.application.commands import EraseAccount
from pit.modules.planning.application.commands import (
    DraftLifePlan,
    EditLifePlanGoal,
    StartLifePlan,
)
from pit.modules.planning.domain.life_plan import GoalAnswers, LifePlanRequest
from pit.modules.planning.domain.plan import PlanStatus
from pit.modules.planning.domain.routine import BusyBlock, DayFrame, check_fits
from pit.shared.domain.errors import DomainError
from tests.application.conftest import World

FRAME = DayFrame(
    wake=time(6, 0),
    sleep=time(23, 0),
    busy=(BusyBlock("Ish", frozenset(range(5)), time(9, 0), time(18, 0)),),
)


def request(duration: int = 60) -> LifePlanRequest:
    return LifePlanRequest(
        goals=(
            GoalAnswers("Kuchli backend dasturchi bo'lish"),
            GoalAnswers("Sport bilan shug'ullanish"),
        ),
        frame=FRAME,
        duration_days=duration,
    )


async def test_two_goals_become_one_clash_free_routine_and_two_challenges(world: World) -> None:
    user = world.add_user()
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    plan = world.store.life_plans[plan_id]
    assert [g.proposal.category.value for g in plan.goals] == ["code", "sport"]
    check_fits(FRAME, [g.proposal.schedule for g in plan.goals])
    assert all(g.proposal.duration_days == 60 for g in plan.goals)
    assert all(g.proposal.roadmap and len(g.proposal.roadmap.months) == 2 for g in plan.goals)

    started = await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=plan_id))
    assert len(started) == 2 and plan.status is PlanStatus.STARTED
    assert {world.participation(p).user_id for p in started} == {user.id}


async def test_editing_a_goal_into_a_clash_is_refused(world: World) -> None:
    user = world.add_user()
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    plan = world.store.life_plans[plan_id]
    other = plan.goals[1].proposal.schedule.week[0][0]
    first = plan.goals[0].proposal.schedule
    clashing = type(first)(
        week=tuple(
            tuple(t.__class__(t.key, t.title, t.minutes, t.required, other.at) for t in day)
            for day in first.week
        )
    )
    with pytest.raises(DomainError):
        await world.bus.handle(
            EditLifePlanGoal(user_id=user.id, plan_id=plan_id, goal_key="g1", schedule=clashing)
        )


async def test_the_morning_is_one_message_and_months_get_their_milestone(world: World) -> None:
    user = world.add_user()
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=plan_id))

    await world.bus.handle(SendDailyNudges(kind="morning"))
    moments = [n.moment for n in world.store.notifications.values()]
    assert moments.count(Moment.MORNING_ROUTINE) + moments.count(Moment.REST_DAY) == 1
    assert Moment.MORNING not in moments

    world.clock.advance(days=30)
    await world.bus.handle(SendDailyNudges(kind="morning"))
    months = [n for n in world.store.notifications.values() if n.moment is Moment.MONTH_STARTED]
    assert len(months) == 2  # one per goal


async def test_erasing_the_account_forgets_the_plans(world: World) -> None:
    user = world.add_user()
    await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    await world.bus.handle(EraseAccount(user_id=user.id, confirm_username=user.username))
    assert world.store.life_plans == {}
