from datetime import date, timedelta

import pytest

from pit.modules.coaching.domain.messages import LIBRARY, QUOTES, Moment, compose, quote_of_the_day

ALL_FACTS = {
    "name": "ali_2008",
    "title": "Har kuni kitob",
    "days": 30,
    "streak": 7,
    "days_left": 12,
    "freezes_left": 1,
    "done": 9,
    "money_line": "Garovingiz (100 000 so'm) to'liq qaytarildi.",
    "reason": "Rasmda kitob ko'rinmadi",
    "tasks": 2,
    "minutes": 45,
    "left": 1,
    "friend": "vali_07",
    "planned": 7,
    "group_line": "Guruhda 2-o'rin. ",
    "emoji": "👏",
}


@pytest.mark.parametrize("moment", list(Moment))
def test_every_phrasing_of_every_moment_renders(moment: Moment) -> None:
    assert LIBRARY[moment], f"{moment} has no messages"
    for title, body in LIBRARY[moment]:
        assert title.format(**ALL_FACTS).strip()
        assert body.format(**ALL_FACTS).strip()


def test_choice_is_stable_for_the_same_moment_and_varies_across_moments() -> None:
    first = compose(Moment.DAY_DONE, seed="day:p1:2026-10-01", **ALL_FACTS)
    assert first == compose(Moment.DAY_DONE, seed="day:p1:2026-10-01", **ALL_FACTS)
    variants = {compose(Moment.DAY_DONE, seed=f"day:p1:{d}", **ALL_FACTS) for d in range(40)}
    assert len(variants) > 1  # the coach does not repeat the same sentence every day


def test_quote_of_the_day_changes_over_a_month() -> None:
    start = date(2026, 10, 1)
    quotes = {quote_of_the_day(start + timedelta(days=i)) for i in range(30)}
    assert len(quotes) > 3 and quotes <= set(QUOTES)
