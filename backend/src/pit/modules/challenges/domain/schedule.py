"""Weekly plan: which tasks happen on which weekday. A weekday with no tasks is a rest day."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, time

from pit.shared.domain.errors import DomainError, InvariantViolation

TASK_KEY_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
MIN_TASK_MINUTES = 5
MAX_DAY_MINUTES = 12 * 60
# A stake must buy real effort, otherwise "5 minutes a week" would be a free refund.
STAKE_MIN_ACTIVE_DAYS = 3
STAKE_MIN_WEEKLY_MINUTES = 90
WEEKDAY_NAMES = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    key: str
    title: str
    minutes: int
    required: bool = True  # required tasks decide the day; optional ones only earn points
    at: time | None = None  # when to do it (local time); the coach reminds at that moment

    def __post_init__(self) -> None:
        if not TASK_KEY_RE.fullmatch(self.key):
            raise InvariantViolation(f"Vazifa kaliti noto'g'ri: {self.key!r}")
        if not self.title.strip() or len(self.title) > 120:
            raise InvariantViolation("Vazifa nomi 1-120 belgi bo'lishi kerak")
        if not MIN_TASK_MINUTES <= self.minutes <= MAX_DAY_MINUTES:
            raise InvariantViolation(f"Vazifa {MIN_TASK_MINUTES} daqiqadan kam bo'lmasin")


@dataclass(frozen=True, slots=True)
class Schedule:
    week: tuple[tuple[TaskSpec, ...], ...]  # index 0 = Monday

    def __post_init__(self) -> None:
        if len(self.week) != 7:
            raise InvariantViolation("Jadval 7 kundan iborat bo'lishi kerak")
        for weekday, tasks in enumerate(self.week):
            name = WEEKDAY_NAMES[weekday]
            keys = [t.key for t in tasks]
            if len(keys) != len(set(keys)):
                raise InvariantViolation(f"{name}: vazifa kalitlari takrorlanmasin")
            if tasks and not any(t.required for t in tasks):
                raise InvariantViolation(f"{name}: kamida bitta majburiy vazifa bo'lsin")
            if sum(t.minutes for t in tasks) > MAX_DAY_MINUTES:
                raise InvariantViolation(f"{name}: bir kunga 12 soatdan ko'p reja qo'yilmaydi")
        if self.active_days_per_week == 0:
            raise InvariantViolation("Haftada kamida bitta ish kuni bo'lishi kerak")

    @classmethod
    def every_day(cls, *tasks: TaskSpec) -> Schedule:
        return cls(week=tuple(tuple(tasks) for _ in range(7)))

    @classmethod
    def by_weekday(cls, plan: Mapping[int, Sequence[TaskSpec]]) -> Schedule:
        return cls(week=tuple(tuple(plan.get(weekday, ())) for weekday in range(7)))

    def tasks_on(self, day: date) -> tuple[TaskSpec, ...]:
        return self.week[day.weekday()]

    def is_active(self, day: date) -> bool:
        return bool(self.tasks_on(day))

    def task(self, day: date, key: str) -> TaskSpec | None:
        return next((t for t in self.tasks_on(day) if t.key == key), None)

    def required_keys_on(self, day: date) -> frozenset[str]:
        return frozenset(t.key for t in self.tasks_on(day) if t.required)

    def minutes_on_weekday(self, weekday: int) -> int:
        return sum(t.minutes for t in self.week[weekday])

    @property
    def active_days_per_week(self) -> int:
        return sum(1 for tasks in self.week if tasks)

    @property
    def required_minutes_per_week(self) -> int:
        return sum(t.minutes for tasks in self.week for t in tasks if t.required)

    def without_times(self) -> Schedule:
        return Schedule(week=tuple(tuple(replace(t, at=None) for t in day) for day in self.week))

    def is_at_least_as_demanding_as(self, other: Schedule) -> bool:
        return (
            self.active_days_per_week >= other.active_days_per_week
            and self.required_minutes_per_week >= other.required_minutes_per_week
        )

    def ensure_stake_worthy(self) -> None:
        if (
            self.active_days_per_week < STAKE_MIN_ACTIVE_DAYS
            or self.required_minutes_per_week < STAKE_MIN_WEEKLY_MINUTES
        ):
            raise DomainError(
                f"Pulli rejim uchun reja haftada kamida {STAKE_MIN_ACTIVE_DAYS} kun va "
                f"{STAKE_MIN_WEEKLY_MINUTES} daqiqa majburiy ish bo'lishi kerak"
            )
