from datetime import time

import pytest

from pit.modules.coaching.application.commands import SendDailyNudges
from pit.modules.coaching.domain.moments import Moment
from pit.modules.identity.application.commands import EraseAccount
from pit.modules.planning.application.commands import (
    ChangeDayFrame,
    DraftLifePlan,
    EditLifePlanGoal,
    RetimeLifePlanRun,
    RetimeTasks,
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


async def test_running_challenges_join_the_routine_and_get_their_times(world: World) -> None:
    user = world.add_user()
    running = await world.join(user, world.add_challenge(duration_days=30))  # task "main", no time
    plan_id = await world.bus.handle(
        DraftLifePlan(
            user_id=user.id,
            request=request(),
            times={running: {"main": time(19, 0)}},
        )
    )
    plan = world.store.life_plans[plan_id]
    assert [run.participation_id for run in plan.existing] == [running]
    assert plan.existing[0].schedule.week[0][0].at == time(19, 0)
    check_fits(
        FRAME,
        [plan.existing[0].schedule, *(g.proposal.schedule for g in plan.goals)],
        fixed=1,
    )

    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=plan_id))
    today_task = world.participation(running).tasks_on(world.today)[0]
    assert today_task.at == time(19, 0) and today_task.minutes == 60  # only the time changed


async def test_a_routine_can_be_just_the_running_challenges(world: World) -> None:
    user = world.add_user()
    running = await world.join(user, world.add_challenge(duration_days=30))
    only_existing = LifePlanRequest(goals=(), frame=FRAME, duration_days=30)
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=only_existing))
    run = world.store.life_plans[plan_id].existing[0]
    assert run.participation_id == running and run.schedule.week[0][0].at is not None

    lonely = world.add_user()
    with pytest.raises(DomainError):
        await world.bus.handle(DraftLifePlan(user_id=lonely.id, request=only_existing))


async def test_a_person_has_one_routine_at_a_time(world: World) -> None:
    user = world.add_user()
    first = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=first))
    second = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request(30)))
    # the first routine's goals are running challenges now, so the new one includes them
    assert len(world.store.life_plans[second].existing) == 2
    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=second))
    assert world.store.life_plans[first].status is PlanStatus.REPLACED
    assert world.store.life_plans[second].status is PlanStatus.STARTED


async def test_the_routine_only_retimes_a_running_challenge(world: World) -> None:
    user = world.add_user()
    running = await world.join(user, world.add_challenge(duration_days=30))
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    run = world.store.life_plans[plan_id].existing[0]
    longer = type(run.schedule)(
        week=tuple(
            tuple(t.__class__(t.key, t.title, t.minutes + 30, t.required, t.at) for t in day)
            for day in run.schedule.week
        )
    )
    with pytest.raises(DomainError):
        await world.bus.handle(
            RetimeLifePlanRun(
                user_id=user.id, plan_id=plan_id, participation_id=running, schedule=longer
            )
        )


async def test_tasks_can_be_moved_by_hand_but_not_onto_commitments(world: World) -> None:
    user = world.add_user()
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=plan_id))
    joined_later = await world.join(user, world.add_challenge(duration_days=30))  # untimed

    await world.bus.handle(
        RetimeTasks(user_id=user.id, participation_id=joined_later, times={"main": time(21, 30)})
    )
    assert world.participation(joined_later).tasks_on(world.today)[0].at == time(21, 30)

    with pytest.raises(DomainError, match="ustma-ust"):  # 10:00 is work time on weekdays
        await world.bus.handle(
            RetimeTasks(user_id=user.id, participation_id=joined_later, times={"main": time(10, 0)})
        )


async def test_the_day_frame_can_change_unless_it_hits_a_task(world: World) -> None:
    user = world.add_user()
    plan_id = await world.bus.handle(DraftLifePlan(user_id=user.id, request=request()))
    await world.bus.handle(StartLifePlan(user_id=user.id, plan_id=plan_id))
    later_sleep = DayFrame(wake=time(6, 0), sleep=time(23, 30), busy=FRAME.busy)
    await world.bus.handle(ChangeDayFrame(user_id=user.id, frame=later_sleep))
    assert world.store.life_plans[plan_id].frame.sleep == time(23, 30)

    all_day_busy = DayFrame(
        wake=time(6, 0),
        sleep=time(23, 0),
        busy=(BusyBlock("Ish", frozenset(range(7)), time(6, 0), time(23, 0)),),
    )
    with pytest.raises(DomainError):
        await world.bus.handle(ChangeDayFrame(user_id=user.id, frame=all_day_busy))
