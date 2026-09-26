from datetime import date
from uuid import uuid4

import pytest

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.participation import Participation
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.shared.domain.errors import DomainError, InvariantViolation
from pit.shared.domain.money import Money
from tests.factories import make_challenge

TODAY = date(2026, 10, 1)  # Thursday
GYM = TaskSpec(key="gym", title="Sport zali", minutes=60)
MON_WED_FRI = Schedule.by_weekday({0: [GYM], 2: [GYM], 4: [GYM]})


def start(schedule: Schedule = MON_WED_FRI, *, stake: int = 0) -> Participation:
    return Participation.start(
        participation_id=uuid4(),
        user_id=uuid4(),
        challenge=make_challenge(duration_days=14, schedule=schedule),
        mode=ParticipationMode.STAKE if stake else ParticipationMode.FREE,
        stake=Money(stake),
        start_date=TODAY,
        today=TODAY,
    )


def test_only_scheduled_days_are_in_the_calendar() -> None:
    p = start()
    # Oct 1-14: Fri 2, Mon 5, Wed 7, Fri 9, Mon 12, Wed 14
    assert list(p.days) == [date(2026, 10, d) for d in (2, 5, 7, 9, 12, 14)]
    assert p.freezes_total == 0  # one freeze per 10 scheduled days


def test_no_proof_on_a_rest_day() -> None:
    with pytest.raises(DomainError, match="dam olish"):
        start().ensure_accepts_proof(TODAY, "gym")


def test_unknown_task_is_refused() -> None:
    with pytest.raises(DomainError, match="bunday vazifa"):
        start().ensure_accepts_proof(date(2026, 10, 2), "reading")


def test_schedule_shape_rules() -> None:
    optional_only = TaskSpec(key="x", title="Qo'shimcha", minutes=10, required=False)
    with pytest.raises(InvariantViolation, match="majburiy"):
        Schedule.by_weekday({0: [optional_only]})
    with pytest.raises(InvariantViolation, match="takrorlanmasin"):
        Schedule.by_weekday({0: [GYM, GYM]})
    with pytest.raises(InvariantViolation, match="kamida bitta ish kuni"):
        Schedule.by_weekday({})


def test_stake_needs_real_effort() -> None:
    with pytest.raises(DomainError, match="3 kun"):
        Schedule.by_weekday({0: [GYM]}).ensure_stake_worthy()
    short = TaskSpec(key="gym", title="Sport", minutes=20)
    with pytest.raises(DomainError, match="90 daqiqa"):
        Schedule.by_weekday({0: [short], 2: [short], 4: [short]}).ensure_stake_worthy()
    MON_WED_FRI.ensure_stake_worthy()


def test_stake_schedule_can_only_get_harder() -> None:
    p = start(stake=50_000)
    half = TaskSpec(key="gym", title="Sport zali", minutes=30)
    easier = Schedule.by_weekday({0: [half], 2: [half], 4: [half]})  # still >= stake minimum
    with pytest.raises(DomainError, match="qiyinlashtirish"):
        p.change_schedule(easier, TODAY)

    harder = Schedule.by_weekday({0: [GYM], 2: [GYM], 4: [GYM], 5: [GYM]})
    p.change_schedule(harder, TODAY)
    assert date(2026, 10, 3) in p.days  # Saturday now counts, from tomorrow on


def test_free_schedule_may_get_easier() -> None:
    p = start()
    p.change_schedule(Schedule.by_weekday({0: [GYM]}), TODAY)
    assert list(p.days) == [date(2026, 10, 5), date(2026, 10, 12)]


def test_days_already_lived_keep_their_plan() -> None:
    p = start()
    p.record_approved_day(date(2026, 10, 2))
    tuesday_reading = Schedule.by_weekday({1: [TaskSpec(key="read", title="Kitob", minutes=30)]})

    p.change_schedule(tuesday_reading, date(2026, 10, 5))  # changed on Monday

    assert date(2026, 10, 5) in p.days  # today stays under the old plan
    assert p.required_tasks(date(2026, 10, 5)) == {"gym"}
    assert date(2026, 10, 6) in p.days and date(2026, 10, 7) not in p.days
    assert p.required_tasks(date(2026, 10, 6)) == {"read"}
