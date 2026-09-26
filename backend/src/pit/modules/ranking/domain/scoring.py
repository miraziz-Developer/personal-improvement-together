from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

# (minimum streak, points per difficulty level) — longer streaks are worth more per day.
STREAK_TIERS = ((30, 20), (14, 15), (7, 12), (1, 10))
COMPLETION_POINTS_PER_WEEK = 50
MIN_COHORT_SIZE = 10
OPTIONAL_TASK_MAX_POINTS = 5  # below the cheapest required day (difficulty 1 = 10 points)


class ScoreReason(StrEnum):
    DAY = "day"
    COMPLETION = "completion"
    OPTIONAL_TASK = "optional_task"


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    """Immutable fact: the user earned points. `source_key` makes awarding idempotent."""

    user_id: UUID
    points: int
    reason: ScoreReason
    source_key: str
    earned_on: date


def day_points(difficulty: int, streak: int) -> int:
    per_level = next(points for min_streak, points in STREAK_TIERS if streak >= min_streak)
    return difficulty * per_level


def completion_bonus(difficulty: int, duration_days: int, *, stake_mode: bool) -> int:
    bonus = COMPLETION_POINTS_PER_WEEK * difficulty * duration_days // 7
    # Putting money on the line earns extra points — never extra money.
    return bonus + bonus // 2 if stake_mode else bonus


def optional_task_points(minutes: int) -> int:
    """Extra work is rewarded, but a required day is always worth more than any single extra."""
    return max(1, min(minutes // 10, OPTIONAL_TASK_MAX_POINTS))


def period_keys(day: date) -> list[str]:
    iso = day.isocalendar()
    return [f"w:{iso.year}-W{iso.week:02d}", f"s:{day:%Y-%m}", "all"]


def leaderboard_keys(*, day: date, birth_year: int, region_id: UUID) -> list[str]:
    scopes = ["global", f"age:{birth_year}", f"region:{region_id}"]
    return [f"lb:{period}:{scope}" for period in period_keys(day) for scope in scopes]
