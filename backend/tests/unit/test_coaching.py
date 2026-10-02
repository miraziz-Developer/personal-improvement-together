from datetime import date, timedelta

import pytest

from pit.modules.coaching.domain.messages import LIBRARY, QUOTES, Moment, compose, quote_of_the_day
from pit.modules.coaching.domain.messages_ru import LIBRARY_RU

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
    "reward": "+1 freeze va +50 ball",
    "planned": 7,
    "group_line": "Guruhda 2-o'rin. ",
    "emoji": "👏",
    "focus_line": "Bugungi mavzu: Funksiyalar. ",
    "task": "Kod yozish",
    "at": "07:00",
    "goals": 2,
    "first": "06:30 — Yugurish",
    "month": 2,
    "done_goal": "Odat shakllandi",
    "goal": "Natija ko'rinadi",
    "tomorrow_line": "Ertaga birinchisi: 06:30 — Yugurish. ",
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


@pytest.mark.parametrize("moment", list(Moment))
def test_every_moment_speaks_russian_too(moment: Moment) -> None:
    assert LIBRARY_RU[moment], f"{moment} has no Russian messages"
    for title, body in LIBRARY_RU[moment]:
        assert title.format(**ALL_FACTS).strip()
        assert body.format(**ALL_FACTS).strip()


def test_sometimes_sentences_follow_the_language() -> None:
    _, uz = compose(
        Moment.CHALLENGE_COMPLETED, seed="x", name="ali", title="Kitob", stake="100 000 so'm"
    )
    _, ru = compose(
        Moment.CHALLENGE_COMPLETED,
        seed="x",
        locale="ru",
        name="ali",
        title="Kitob",
        stake="100 000 so'm",
    )
    assert "to'liq qaytarildi" in uz and "полностью возвращена" in ru
    _, free = compose(
        Moment.CHALLENGE_COMPLETED, seed="x", locale="ru", name="ali", title="Kitob", stake=""
    )
    assert "ставка" not in free
    assert quote_of_the_day(date(2026, 10, 1), "ru") != quote_of_the_day(date(2026, 10, 1))
