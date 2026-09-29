from datetime import timedelta

import pytest

from pit.modules.challenges.application.commands import LeaveChallenge, PauseChallenge
from pit.modules.challenges.domain.participation import DayStatus, ParticipationStatus
from pit.shared.domain.errors import DomainError
from tests.application.conftest import World


async def test_a_pause_keeps_the_streak_and_makes_the_run_longer(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=7))  # no freezes at all
    await world.prove(user, pid, photo=False)  # day 1 done
    run = world.participation(pid)
    end_before = run.end_date

    first = await world.bus.handle(PauseChallenge(user_id=user.id, participation_id=pid, days=2))
    assert first == world.today + timedelta(days=1)  # today is already done
    assert run.end_date == end_before + timedelta(days=2) and run.total_days == 7
    assert run.tasks_on(first) == ()  # a paused day asks for nothing

    for _ in range(3):  # two paused days pass without proofs: nothing breaks
        await world.next_day()
    assert run.status is ParticipationStatus.ACTIVE and run.current_streak == 1
    assert list(run.days.values()).count(DayStatus.PAUSED) == 2

    for _ in range(6):
        await world.prove(user, pid, photo=False)
        await world.next_day()
    assert run.status is ParticipationStatus.COMPLETED and run.days_completed == 7


async def test_pauses_are_limited_and_not_for_stakes(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=30))
    await world.bus.handle(PauseChallenge(user_id=user.id, participation_id=pid, days=10))
    with pytest.raises(DomainError, match="qolgani: 4"):
        await world.bus.handle(PauseChallenge(user_id=user.id, participation_id=pid, days=5))

    rich = world.add_user()
    await world.deposit(rich, 200_000)
    staked = await world.join(rich, world.add_challenge(duration_days=30), stake=50_000)
    await world.next_day()
    with pytest.raises(DomainError):
        await world.bus.handle(PauseChallenge(user_id=rich.id, participation_id=staked, days=1))
    with pytest.raises(DomainError):
        await world.bus.handle(LeaveChallenge(user_id=rich.id, participation_id=staked))


async def test_leaving_a_free_challenge_ends_it_quietly(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=30))
    await world.next_day()
    await world.bus.handle(LeaveChallenge(user_id=user.id, participation_id=pid))
    run = world.participation(pid)
    assert run.status is ParticipationStatus.CANCELLED and not run.is_open
    with pytest.raises(DomainError):
        await world.bus.handle(LeaveChallenge(user_id=user.id, participation_id=pid))
