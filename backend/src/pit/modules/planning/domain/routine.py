"""The shape of the user's day, and fitting several goals' tasks into it without clashes.

Times are local wall-clock times. A day runs from waking up to going to sleep (both on the same
calendar day); fixed commitments (work, school) are carved out of it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import time

from pit.modules.challenges.domain.schedule import WEEKDAY_NAMES, Schedule, TaskSpec
from pit.shared.domain.errors import DomainError, InvariantViolation

LOAD_SHARE = 0.8  # plans take at most 80% of the free time — life needs room too
WAKE_UP_MINUTES = 15  # nobody starts a task the minute the alarm rings
GAP_MINUTES = 10  # a breather between two tasks
MIN_SLOT_MINUTES = 15  # shorter gaps in the day are not worth planning into
MIN_AWAKE_MINUTES = 6 * 60
MAX_BUSY_BLOCKS = 6
MAX_LABEL = 40

type Span = tuple[int, int]  # [start, end) in minutes since midnight


def minutes_of(moment: time) -> int:
    return moment.hour * 60 + moment.minute


def clock(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


def _overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


@dataclass(frozen=True, slots=True)
class BusyBlock:
    """A fixed commitment the plan must work around, e.g. work Mon-Fri 09:00-18:00."""

    label: str
    weekdays: frozenset[int]  # 0 = Monday
    start: time
    end: time

    def __post_init__(self) -> None:
        if not self.label.strip() or len(self.label) > MAX_LABEL:
            raise InvariantViolation(f"Band vaqt nomi 1-{MAX_LABEL} belgi bo'lsin")
        if not self.weekdays or not self.weekdays <= set(range(7)):
            raise InvariantViolation("Band vaqt uchun kamida bitta hafta kuni tanlang")
        if self.end <= self.start:
            raise InvariantViolation(f"{self.label}: tugash vaqti boshlanishidan keyin bo'lsin")

    @property
    def span(self) -> Span:
        return minutes_of(self.start), minutes_of(self.end)


@dataclass(frozen=True, slots=True)
class DayFrame:
    wake: time
    sleep: time
    busy: tuple[BusyBlock, ...] = ()

    def __post_init__(self) -> None:
        if minutes_of(self.sleep) - minutes_of(self.wake) < MIN_AWAKE_MINUTES:
            raise InvariantViolation(
                "Uyg'onish va uxlash vaqti orasida kamida 6 soat bo'lsin (uxlash yarim tungacha)"
            )
        if len(self.busy) > MAX_BUSY_BLOCKS:
            raise InvariantViolation(f"Band vaqtlar {MAX_BUSY_BLOCKS} tadan oshmasin")

    @property
    def awake(self) -> Span:
        return minutes_of(self.wake) + WAKE_UP_MINUTES, minutes_of(self.sleep)

    def busy_on(self, weekday: int) -> list[BusyBlock]:
        return sorted((b for b in self.busy if weekday in b.weekdays), key=lambda b: b.start)

    def free_windows(self, weekday: int) -> list[Span]:
        windows: list[Span] = []
        cursor, end = self.awake
        for block in self.busy_on(weekday):
            start, stop = block.span
            if start > cursor:
                windows.append((cursor, min(start, end)))
            cursor = max(cursor, stop)
        if cursor < end:
            windows.append((cursor, end))
        return [w for w in windows if w[1] - w[0] >= MIN_SLOT_MINUTES]

    def free_minutes(self, weekday: int) -> int:
        return sum(stop - start for start, stop in self.free_windows(weekday))

    def budget(self, weekday: int) -> int:
        return int(self.free_minutes(weekday) * LOAD_SHARE)


def check_fits(frame: DayFrame, schedules: Sequence[Schedule], *, fixed: int = 0) -> None:
    """Every task has a time, lies in free time, and no two tasks of any goal clash. The first
    `fixed` schedules are challenges already running: they may use more than the 80% on
    their own (that promise was made before), but then nothing new fits beside them."""
    for weekday, name in enumerate(WEEKDAY_NAMES):
        taken: list[tuple[Span, str]] = [(b.span, b.label) for b in frame.busy_on(weekday)]
        start_of_day, end_of_day = minutes_of(frame.wake), minutes_of(frame.sleep)
        planned = planned_new = 0
        for index, schedule in enumerate(schedules):
            for task in schedule.week[weekday]:
                if task.at is None:
                    raise DomainError(f"{name}: «{task.title}» uchun vaqt belgilang")
                span = (minutes_of(task.at), minutes_of(task.at) + task.minutes)
                if span[0] < start_of_day or span[1] > end_of_day:
                    raise DomainError(f"{name}: «{task.title}» uyg'oq vaqtingizdan tashqarida")
                clash = next((label for other, label in taken if _overlaps(span, other)), None)
                if clash is not None:
                    raise DomainError(f"{name}: «{task.title}» va «{clash}» vaqti ustma-ust tushdi")
                taken.append((span, task.title))
                planned += task.minutes
                planned_new += task.minutes if index >= fixed else 0
        if planned_new and planned > frame.budget(weekday):
            raise DomainError(
                f"{name}: reja {planned} daqiqa, bo'sh vaqtingizning 80% i esa "
                f"{frame.budget(weekday)} daqiqa"
            )


def _padded(taken: list[Span]) -> list[Span]:
    return [(a - GAP_MINUTES, b + GAP_MINUTES) for a, b in taken]


def _first_slot(
    windows: list[Span], taken: list[Span], length: int, not_before: int = 0
) -> int | None:
    """Earliest start (not before `not_before`) in a free window that keeps a gap to every
    task already placed."""
    blocked = _padded(taken)
    for window_start, window_end in windows:
        cursor = max(window_start, not_before)
        while cursor + length <= window_end:
            clash = [b for b in blocked if _overlaps((cursor, cursor + length), b)]
            if not clash:
                return cursor
            cursor = max(b[1] for b in clash)
    return None


def pack(frame: DayFrame, schedules: Sequence[Schedule], *, fixed: int = 0) -> list[Schedule]:
    """Give every task a clash-free time inside the free windows. A time the task already has
    is kept when it fits; otherwise the earliest free slot is used. Goals earlier in the list
    and required tasks go first; what does not fit is shortened (required) or dropped.

    The first `fixed` schedules are challenges already running: they go first and only get
    times — never shortened or dropped. One that cannot be placed at all is an error."""
    weeks: list[list[list[TaskSpec]]] = [[[] for _ in range(7)] for _ in schedules]
    for weekday in range(7):
        windows = frame.free_windows(weekday)
        taken: list[Span] = []
        left = frame.budget(weekday)
        main_ends: dict[int, int] = {}  # goal -> end of its last required task today
        order = [
            (goal, task)
            for goal, schedule in enumerate(schedules[:fixed])
            for task in schedule.week[weekday]
        ] + [
            (goal, task)
            for required in (True, False)
            for goal, schedule in enumerate(schedules)
            if goal >= fixed
            for task in schedule.week[weekday]
            if task.required is required
        ]
        for goal, task in order:
            keep = goal < fixed
            length = task.minutes if keep else min(task.minutes, left)
            if length < MIN_SLOT_MINUTES and not keep:
                continue
            wanted = minutes_of(task.at) if task.at else None
            start: int | None = None
            if (
                wanted is not None
                and any(w[0] <= wanted and wanted + length <= w[1] for w in windows)
                and not any(_overlaps((wanted, wanted + length), b) for b in _padded(taken))
            ):
                start = wanted
            else:
                # An extra ("read the notes") belongs after the goal's main work, if possible.
                after = 0 if task.required else main_ends.get(goal, 0)
                start = _first_slot(windows, taken, length, after)
                if start is None and after:
                    start = _first_slot(windows, taken, length)
            while start is None and length > MIN_SLOT_MINUTES and task.required and not keep:
                length = max(MIN_SLOT_MINUTES, length - 15)
                start = _first_slot(windows, taken, length)
            if start is None and keep:
                raise DomainError(
                    f"{WEEKDAY_NAMES[weekday]}: «{task.title}» uchun bo'sh vaqt topilmadi"
                )
            if start is None:
                continue
            taken.append((start, start + length))
            left -= length
            if task.required:
                main_ends[goal] = max(main_ends.get(goal, 0), start + length)
            weeks[goal][weekday].append(replace(task, minutes=length, at=clock(start)))
    result: list[Schedule] = []
    for index, week in enumerate(weeks):
        days = []
        for tasks in week:
            tasks.sort(key=lambda t: t.at or time(0))
            if index < fixed:
                days.append(tuple(tasks))  # kept as the challenge defines it
            else:
                days.append(tuple(tasks) if any(t.required for t in tasks) else ())
        if index < fixed:
            result.append(_in_original_order(schedules[index], days))
            continue
        if not any(days):
            raise DomainError("Kun tartibingizda bu maqsad uchun bo'sh vaqt qolmadi")
        result.append(Schedule(week=tuple(days)))
    return result


def _in_original_order(original: Schedule, placed: list[tuple[TaskSpec, ...]]) -> Schedule:
    """A running challenge keeps its task order; only the times are new
    (Participation.retime accepts nothing else)."""
    week = []
    for day, tasks in zip(original.week, placed, strict=True):
        times = {t.key: t.at for t in tasks}
        week.append(tuple(replace(t, at=times[t.key]) for t in day))
    return Schedule(week=tuple(week))
