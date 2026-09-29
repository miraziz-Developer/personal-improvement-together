from datetime import time

from pit.modules.challenges.domain.roadmap import Milestone, Roadmap
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.coaching.application.commands import SendDailyNudges, SendTaskReminders
from pit.modules.coaching.domain.moments import Moment
from pit.modules.identity.application.commands import ChangeLocale
from tests.application.conftest import World

# The world's clock starts at 09:00 Tashkent time.
SCHEDULE = Schedule.every_day(TaskSpec("main", "Kod yozish", 45, at=time(9, 30)))
ROADMAP = Roadmap(outcome="Loyiha", weeks=(Milestone("Asoslar", "Asos", ("O'zgaruvchilar",)),))


def due(world: World) -> list[str]:
    return [n.body for n in world.store.notifications.values() if n.moment is Moment.TASK_DUE]


async def test_the_coach_reminds_when_the_tasks_time_comes(world: World) -> None:
    user = world.add_user()
    await world.join(user, world.add_challenge(schedule=SCHEDULE, roadmap=ROADMAP))

    await world.bus.handle(SendTaskReminders())
    assert due(world) == []  # 09:00 — too early

    world.clock.advance(minutes=35)
    await world.bus.handle(SendTaskReminders())
    await world.bus.handle(SendTaskReminders())  # the job runs every few minutes
    assert len(due(world)) == 1
    assert "09:30" in due(world)[0] and "O'zgaruvchilar" in due(world)[0]

    world.clock.advance(hours=2)
    await world.bus.handle(SendTaskReminders())
    assert len(due(world)) == 1  # a late reminder would only nag


async def test_no_reminder_for_a_task_already_proven(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(schedule=SCHEDULE))
    await world.prove(user, pid)
    world.clock.advance(minutes=35)
    await world.bus.handle(SendTaskReminders())
    assert due(world) == []


async def test_the_morning_message_names_todays_lesson(world: World) -> None:
    user = world.add_user()
    await world.join(user, world.add_challenge(schedule=SCHEDULE, roadmap=ROADMAP))
    await world.bus.handle(SendDailyNudges(kind="morning"))
    morning = [n for n in world.store.notifications.values() if n.moment is Moment.MORNING]
    assert "O'zgaruvchilar" in morning[0].body


async def test_the_ai_checks_the_proof_against_todays_lesson(world: World) -> None:
    user = world.add_user()
    await world.bus.handle(ChangeLocale(user_id=user.id, locale="ru"))
    pid = await world.join(user, world.add_challenge(schedule=SCHEDULE, roadmap=ROADMAP))
    await world.prove(user, pid)
    request = world.verifier.requests[-1]
    assert request.lesson == "O'zgaruvchilar" and request.language == "ru"
