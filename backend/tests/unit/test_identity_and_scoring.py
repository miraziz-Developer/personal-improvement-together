from datetime import date
from uuid import uuid4

import pytest

from pit.modules.identity.domain.user import User, age_on
from pit.modules.ranking.domain.scoring import completion_bonus, day_points, leaderboard_keys
from pit.shared.domain.errors import DomainError, InvariantViolation

TODAY = date(2026, 9, 24)


def register(birth_date: date, username: str = "ali_2008") -> User:
    return User.register(
        user_id=uuid4(), username=username, birth_date=birth_date, region_id=uuid4(), today=TODAY
    )


def test_age_counts_the_birthday_exactly() -> None:
    assert age_on(date(2008, 9, 25), TODAY) == 17  # birthday is tomorrow
    assert age_on(date(2008, 9, 24), TODAY) == 18


def test_any_age_can_stake_once_phone_is_verified() -> None:
    child = register(date(2016, 1, 1))  # 10 years old; the parent pays
    with pytest.raises(DomainError):
        child.ensure_can_stake()
    child.verify_phone("+998 90 123 45 67")
    child.ensure_can_stake()


def test_username_rules() -> None:
    with pytest.raises(InvariantViolation):
        register(date(2000, 1, 1), username="a!")
    assert register(date(2000, 1, 1), username="  Ali_2008 ").username == "ali_2008"


def test_streak_tiers_and_bonuses() -> None:
    assert [day_points(2, s) for s in (1, 7, 14, 30)] == [20, 24, 30, 40]
    assert completion_bonus(2, 7, stake_mode=False) == 100
    assert completion_bonus(2, 7, stake_mode=True) == 150


def test_leaderboard_keys_cover_week_season_and_all_time_for_each_scope() -> None:
    region = uuid4()
    keys = leaderboard_keys(day=date(2026, 9, 24), birth_year=2008, region_id=region)
    assert "lb:w:2026-W39:age:2008" in keys
    assert f"lb:s:2026-09:region:{region}" in keys
    assert "lb:all:global" in keys
    assert len(keys) == 9


def test_anyone_from_seven_years_old_can_register() -> None:
    assert register(date(2019, 9, 24)).birth_year == 2019  # exactly 7 today
    with pytest.raises(InvariantViolation):
        register(date(2019, 9, 25))  # 7 tomorrow
