from datetime import time

import pytest

from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.planning.domain.routine import BusyBlock, DayFrame, check_fits, pack
from pit.shared.domain.errors import DomainError, InvariantViolation

WORK = BusyBlock("Ish", frozenset(range(5)), time(9, 0), time(18, 0))
FRAME = DayFrame(wake=time(6, 0), sleep=time(23, 0), busy=(WORK,))


def daily(*tasks: TaskSpec) -> Schedule:
    return Schedule.every_day(*tasks)


def test_free_time_is_the_awake_day_minus_commitments() -> None:
    assert FRAME.free_windows(0) == [(375, 540), (1080, 1380)]  # 06:15-09:00, 18:00-23:00
    assert FRAME.free_windows(6) == [(375, 1380)]  # Sunday: no work
    assert FRAME.budget(0) == int((165 + 300) * 0.8)


def test_a_frame_needs_a_real_day() -> None:
    with pytest.raises(InvariantViolation):
        DayFrame(wake=time(7, 0), sleep=time(10, 0))
    with pytest.raises(InvariantViolation):
        BusyBlock("Ish", frozenset({0}), time(18, 0), time(9, 0))


def test_packing_keeps_good_times_and_moves_clashes() -> None:
    run = daily(TaskSpec("run", "Yugurish", 40, at=time(6, 30)))
    code = daily(TaskSpec("code", "Kod", 60, at=time(6, 30)))  # clashes with the run
    sport, coding = pack(FRAME, [run, code])
    assert sport.week[0][0].at == time(6, 30)
    assert coding.week[0][0].at == time(7, 20)  # after the run and a 10-minute breather
    check_fits(FRAME, [sport, coding])


def test_packing_never_touches_work_hours() -> None:
    long = daily(TaskSpec("code", "Kod", 150, at=time(10, 0)))
    (packed,) = pack(FRAME, [long])
    start = packed.week[0][0].at
    assert start is not None and not time(9, 0) <= start < time(18, 0)
    check_fits(FRAME, [packed])


def test_a_goal_with_no_room_at_all_is_refused() -> None:
    tight = DayFrame(
        wake=time(6, 0),
        sleep=time(13, 0),
        busy=(BusyBlock("Ish", frozenset(range(7)), time(6, 30), time(13, 0)),),
    )
    with pytest.raises(DomainError):
        pack(tight, [daily(TaskSpec("code", "Kod", 60))])


def test_check_fits_names_the_problem() -> None:
    no_time = daily(TaskSpec("code", "Kod", 60))
    with pytest.raises(DomainError, match="vaqt belgilang"):
        check_fits(FRAME, [no_time])
    at_work = daily(TaskSpec("code", "Kod", 60, at=time(10, 0)))
    with pytest.raises(DomainError, match="ustma-ust"):
        check_fits(FRAME, [at_work])
    night = daily(TaskSpec("code", "Kod", 60, at=time(22, 30)))
    with pytest.raises(DomainError, match="tashqarida"):
        check_fits(FRAME, [night])
