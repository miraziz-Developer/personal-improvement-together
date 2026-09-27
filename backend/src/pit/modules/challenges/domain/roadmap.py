"""Roadmap: where a challenge leads, week by week. The schedule says *when* you work; the
roadmap says *what* you work on — so day 12 moves you further than day 2 instead of repeating it."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from pit.shared.domain.errors import InvariantViolation

MAX_WEEKS = 13  # the longest challenge is 90 days
MAX_LESSONS_PER_WEEK = 7
MAX_TEXT = 200


def _check(text: str, what: str) -> None:
    if not text.strip() or len(text) > MAX_TEXT:
        raise InvariantViolation(f"{what}: 1-{MAX_TEXT} belgi bo'lishi kerak")


@dataclass(frozen=True, slots=True)
class Milestone:
    """One week of the roadmap."""

    theme: str  # "Python asoslari"
    goal: str  # what you can do when the week is over
    lessons: tuple[str, ...] = ()  # the focus of each working day of the week, in order

    def __post_init__(self) -> None:
        _check(self.theme, "Hafta mavzusi")
        _check(self.goal, "Hafta maqsadi")
        if len(self.lessons) > MAX_LESSONS_PER_WEEK:
            raise InvariantViolation("Haftada 7 tadan ortiq dars bo'lmaydi")
        for lesson in self.lessons:
            _check(lesson, "Dars")


@dataclass(frozen=True, slots=True)
class Focus:
    """What today is about."""

    week: int  # 1-based
    weeks: int
    theme: str
    goal: str
    lesson: str | None  # None when the week has no lesson written for this day


@dataclass(frozen=True, slots=True)
class Roadmap:
    outcome: str  # where you stand on the last day
    weeks: tuple[Milestone, ...]

    def __post_init__(self) -> None:
        _check(self.outcome, "Yakuniy natija")
        if not 1 <= len(self.weeks) <= MAX_WEEKS:
            raise InvariantViolation(f"Yo'l xaritasi 1-{MAX_WEEKS} haftadan iborat bo'lsin")

    def focus(self, start: date, working_days: Iterable[date], day: date) -> Focus | None:
        """Today's place on the roadmap. Weeks count from the start date; within a week the
        n-th working day gets the n-th lesson. Past the last week the last one continues.
        A rest day keeps the week's theme but has no lesson."""
        if day < start:
            return None
        working = set(working_days)
        index = (day - start).days // 7
        milestone = self.weeks[min(index, len(self.weeks) - 1)]
        week_start = start.toordinal() + index * 7
        earlier = sum(1 for d in working if week_start <= d.toordinal() < day.toordinal())
        lesson = milestone.lessons[earlier] if earlier < len(milestone.lessons) else None
        if index >= len(self.weeks) or day not in working:
            lesson = None  # beyond the written roadmap: keep the theme, no invented lessons
        return Focus(
            week=min(index, len(self.weeks) - 1) + 1,
            weeks=len(self.weeks),
            theme=milestone.theme,
            goal=milestone.goal,
            lesson=lesson,
        )
