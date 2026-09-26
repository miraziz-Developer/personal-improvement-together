import re
from datetime import date
from uuid import uuid4

import pytest

from pit.modules.coaching.application.commands import SendDailyNudges
from pit.modules.coaching.domain.messages import Moment
from pit.modules.identity.application.commands import ConfirmPhone, RegisterUser, RequestPhoneCode
from pit.modules.identity.domain.user import CURRENT_TERMS_VERSION
from pit.shared.domain.errors import DomainError, InvariantViolation
from tests.application.conftest import World


def moments(world: World) -> list[Moment]:
    ordered = sorted(world.store.notifications.values(), key=lambda n: n.created_at)
    return [n.moment for n in ordered]


# --- identity ------------------------------------------------------------------------------


async def register(world: World, username: str = "ali_2008", password: str = "parol-2008") -> None:
    await world.bus.handle(
        RegisterUser(
            username=username,
            password=password,
            birth_date=date(2008, 3, 1),
            region_id=uuid4(),
            accepted_terms_version=CURRENT_TERMS_VERSION,
        )
    )


async def test_username_must_be_unique_and_password_strong(world: World) -> None:
    await register(world)
    with pytest.raises(DomainError, match="band"):
        await register(world, "Ali_2008")
    with pytest.raises(InvariantViolation, match="8 belgi"):
        await register(world, "boshqa", "qisqa1")


async def test_registration_requires_accepting_the_current_terms(world: World) -> None:
    fields = {"username": "ali_2008", "password": "parol-2008", "birth_date": date(2008, 3, 1)}
    with pytest.raises(DomainError, match="rozilik"):
        await world.bus.handle(RegisterUser(**fields, region_id=uuid4()))
    with pytest.raises(DomainError, match="yangilangan"):
        await world.bus.handle(
            RegisterUser(**fields, region_id=uuid4(), accepted_terms_version="2020-01-01")
        )

    await register(world)
    (user,) = world.store.users.values()
    assert user.terms_version == CURRENT_TERMS_VERSION
    assert user.terms_accepted_at == world.clock.now()


async def test_phone_is_verified_only_with_the_right_code(world: World) -> None:
    user = world.add_user(phone=False)
    await world.bus.handle(RequestPhoneCode(user_id=user.id, phone="+998 90 111 22 33"))
    code = re.search(r"\d{6}", world.sms.sent[-1][1])
    assert code is not None and world.sms.sent[-1][0] == "+998901112233"

    with pytest.raises(DomainError, match="Kod"):
        await world.bus.handle(ConfirmPhone(user_id=user.id, code="000000"))
    await world.bus.handle(ConfirmPhone(user_id=user.id, code=code.group()))
    assert world.store.users[user.id].phone_verified


# --- the coach -----------------------------------------------------------------------------


async def test_coach_greets_cheers_and_celebrates_milestones(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=7))
    for _ in range(3):
        await world.prove(user, pid)
        await world.next_day()

    assert moments(world) == [
        Moment.CHALLENGE_STARTED,
        Moment.DAY_DONE,
        Moment.DAY_DONE,
        Moment.STREAK_MILESTONE,  # 3 days in a row
    ]
    milestone = max(world.store.notifications.values(), key=lambda n: n.created_at)
    assert "3" in milestone.title or "3" in milestone.body


async def test_coach_supports_after_a_missed_day_and_after_failure(world: World) -> None:
    user = world.add_user()
    await world.join(user, world.add_challenge(duration_days=14))  # 1 freeze
    await world.next_day()
    await world.next_day()

    assert moments(world)[-2:] == [Moment.DAY_FROZEN, Moment.CHALLENGE_FAILED]
    failed = [n for n in world.store.notifications.values() if n.moment is Moment.CHALLENGE_FAILED]
    assert "oxiri emas" in failed[0].title or "tajriba" in failed[0].title.lower()


async def test_morning_plan_and_evening_reminder_are_sent_once(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge())

    await world.bus.handle(SendDailyNudges(kind="morning"))
    await world.bus.handle(SendDailyNudges(kind="morning"))  # the job may run twice
    await world.bus.handle(SendDailyNudges(kind="evening"))
    assert moments(world).count(Moment.MORNING) == 1
    assert moments(world).count(Moment.EVENING_REMINDER) == 1

    await world.prove(user, pid)
    world.clock.advance(minutes=1)
    evening_count = moments(world).count(Moment.EVENING_REMINDER)
    await world.bus.handle(SendDailyNudges(kind="evening"))
    assert moments(world).count(Moment.EVENING_REMINDER) == evening_count  # nothing left to do
