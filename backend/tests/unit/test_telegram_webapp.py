from datetime import UTC, datetime, timedelta

import pytest

from pit.api.telegram_webapp import InvalidInitData, verify_init_data
from tests.fakes import signed_init_data

TOKEN = "123456:bot-token"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def test_telegram_vouches_for_the_user() -> None:
    user = verify_init_data(signed_init_data(TOKEN, 42, NOW), TOKEN, NOW)
    assert (user.id, user.username, user.first_name) == (42, "ali_tg", "Ali")


@pytest.mark.parametrize(
    ("data", "token", "now"),
    [
        (signed_init_data(TOKEN, 42, NOW), "999:other-bot", NOW),  # another bot signed it
        (signed_init_data(TOKEN, 42, NOW).replace("42", "43"), TOKEN, NOW),  # changed user
        (signed_init_data(TOKEN, 42, NOW), TOKEN, NOW + timedelta(days=2)),  # replayed later
        ("user=%7B%7D", TOKEN, NOW),  # no signature at all
    ],
)
def test_anything_else_is_refused(data: str, token: str, now: datetime) -> None:
    with pytest.raises(InvalidInitData):
        verify_init_data(data, token, now)
