from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from uuid import UUID

from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.events import (
    DayCompleted,
    DayFrozen,
    DayNeedsHumanReview,
    OptionalTaskCompleted,
    ParticipationCancelled,
    ParticipationCompleted,
    ParticipationFailed,
    ParticipationStarted,
    ScheduleChanged,
)
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvalidStateTransition, InvariantViolation
from pit.shared.domain.money import Money

DAYS_PER_FREEZE = 10  # one freeze per 10 *scheduled* days
MAX_OPEN_STAKES = 3
MAX_START_DELAY_DAYS = 30


class ParticipationStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


OPEN_STATUSES = frozenset({ParticipationStatus.SCHEDULED, ParticipationStatus.ACTIVE})


class DayStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FROZEN = "frozen"
    MISSED = "missed"
    AWAITING_REVIEW = "awaiting_review"


class DayEvidence(StrEnum):
    """What the verification module knows about a day's *required* tasks, combined."""

    NONE = "none"
    APPROVED = "approved"
    PENDING = "pending"
    AI_REJECTED = "ai_rejected"
    HUMAN_REJECTED = "human_rejected"


def _scheduled_days(first: date, last: date, schedule: Schedule) -> dict[date, DayStatus]:
    span = (last - first).days + 1
    days = (first + timedelta(days=i) for i in range(span))
    return {d: DayStatus.PENDING for d in days if schedule.is_active(d)}


@dataclass(eq=False, kw_only=True)
class Participation(AggregateRoot):
    """One user's run through one challenge — owns the calendar, tasks, streak and outcome.

    Only scheduled days are in `days`: rest days can never be missed.
    """

    user_id: UUID
    challenge_id: UUID
    mode: ParticipationMode
    stake: Money
    difficulty: int
    start_date: date
    duration_days: int
    status: ParticipationStatus
    # (effective from, schedule): past days keep the plan they were lived under.
    schedule_history: list[tuple[date, Schedule]]
    days: dict[date, DayStatus]
    freezes_total: int
    freezes_used: int = 0
    current_streak: int = 0
    best_streak: int = 0
    group_id: UUID | None = None
    finished_on: date | None = None

    @classmethod
    def start(
        cls,
        *,
        participation_id: UUID,
        user_id: UUID,
        challenge: Challenge,
        mode: ParticipationMode,
        stake: Money,
        start_date: date,
        today: date,
        schedule: Schedule | None = None,
        group_id: UUID | None = None,
    ) -> Participation:
        challenge.ensure_joinable(mode, stake)
        schedule = schedule or challenge.default_schedule
        challenge.ensure_schedule_allowed(mode, schedule)
        if start_date < today:
            raise InvariantViolation("Challenge o'tgan sanadan boshlanishi mumkin emas")
        if start_date > today + timedelta(days=MAX_START_DELAY_DAYS):
            raise InvariantViolation(
                f"Boshlanish sanasi {MAX_START_DELAY_DAYS} kundan uzoq bo'lmasin"
            )
        end_date = start_date + timedelta(days=challenge.duration_days - 1)
        days = _scheduled_days(start_date, end_date, schedule)
        participation = cls(
            id=participation_id,
            user_id=user_id,
            challenge_id=challenge.id,
            mode=mode,
            stake=stake,
            difficulty=challenge.difficulty,
            start_date=start_date,
            duration_days=challenge.duration_days,
            status=ParticipationStatus.SCHEDULED,
            schedule_history=[(start_date, schedule)],
            days=days,
            freezes_total=len(days) // DAYS_PER_FREEZE,
            group_id=group_id,
        )
        participation._record(
            ParticipationStarted(
                participation_id=participation_id,
                user_id=user_id,
                challenge_id=challenge.id,
                mode=mode,
                stake=stake,
            )
        )
        participation.activate(today)
        return participation

    # --- Queries -----------------------------------------------------------------------

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days - 1)

    @property
    def is_stake(self) -> bool:
        return self.mode is ParticipationMode.STAKE

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def current_schedule(self) -> Schedule:
        return self.schedule_history[-1][1]

    @property
    def days_completed(self) -> int:
        return sum(1 for s in self.days.values() if s is DayStatus.DONE)

    @property
    def freezes_left(self) -> int:
        return self.freezes_total - self.freezes_used

    def schedule_on(self, day: date) -> Schedule:
        return next(s for since, s in reversed(self.schedule_history) if since <= day)

    def tasks_on(self, day: date) -> tuple[TaskSpec, ...]:
        return self.schedule_on(day).tasks_on(day) if day in self.days else ()

    def task(self, day: date, key: str) -> TaskSpec | None:
        return self.schedule_on(day).task(day, key) if day in self.days else None

    def required_tasks(self, day: date) -> frozenset[str]:
        return self.schedule_on(day).required_keys_on(day)

    def day_status(self, day: date) -> DayStatus:
        if day not in self.days:
            raise InvariantViolation(f"{day} reja bo'yicha ish kuni emas")
        return self.days[day]

    def days_to_settle(self, today: date) -> list[date]:
        """Days that are over but not yet judged. The daily job settles them in order."""
        return [d for d, s in sorted(self.days.items()) if d < today and s is DayStatus.PENDING]

    # --- Lifecycle ---------------------------------------------------------------------

    def attach_to_group(self, group_id: UUID) -> None:
        """The owner of a new "Together" group brings their running participation into it."""
        if self.group_id is not None and self.group_id != group_id:
            raise InvalidStateTransition("Bu challenge allaqachon boshqa guruhda")
        if not self.is_open:
            raise InvalidStateTransition("Tugagan challenge'ga do'st taklif qilib bo'lmaydi")
        self.group_id = group_id

    def activate(self, today: date) -> None:
        if self.status is ParticipationStatus.SCHEDULED and today >= self.start_date:
            self.status = ParticipationStatus.ACTIVE

    def cancel(self, today: date) -> None:
        # Once started, walking away counts as failing — otherwise a stake is no commitment.
        if self.status is not ParticipationStatus.SCHEDULED or today >= self.start_date:
            raise InvalidStateTransition("Faqat hali boshlanmagan challenge'ni bekor qilish mumkin")
        self.status = ParticipationStatus.CANCELLED
        self.finished_on = today
        self._record(
            ParticipationCancelled(
                participation_id=self.id, user_id=self.user_id, mode=self.mode, stake=self.stake
            )
        )

    def change_schedule(self, new: Schedule, today: date) -> None:
        """Takes effect from tomorrow; days already lived keep their plan.

        Stake mode may only get harder — otherwise a user could shrink the plan to nothing
        on a bad day and still get the money back.
        """
        if not self.is_open:
            raise InvalidStateTransition("Tugagan challenge rejasini o'zgartirib bo'lmaydi")
        if self.is_stake:
            new.ensure_stake_worthy()
            if not new.is_at_least_as_demanding_as(self.current_schedule):
                raise DomainError("Pulli rejimda rejani faqat qiyinlashtirish mumkin")
        effective = max(today + timedelta(days=1), self.start_date)
        if effective > self.end_date:
            raise DomainError("Challenge oxirgi kunida rejani o'zgartirib bo'lmaydi")
        kept = {d: s for d, s in self.days.items() if d < effective}  # future days are pending
        self.days = kept | _scheduled_days(effective, self.end_date, new)
        self.schedule_history.append((effective, new))
        self.freezes_total = max(self.freezes_used, len(self.days) // DAYS_PER_FREEZE)
        self._record(ScheduleChanged(participation_id=self.id, effective_from=effective))
        self._complete_if_finished()

    def ensure_accepts_proof(self, day: date, task_key: str) -> None:
        if self.status is not ParticipationStatus.ACTIVE:
            raise InvalidStateTransition("Challenge faol emas")
        if day not in self.days:
            raise DomainError("Bugun reja bo'yicha dam olish kuni")
        task = self.task(day, task_key)
        if task is None:
            raise DomainError("Bugungi rejada bunday vazifa yo'q")
        state = self.days[day]
        if state is DayStatus.PENDING:
            return
        if state is DayStatus.DONE and not task.required:
            return  # optional tasks still earn points after the day is secured
        if state is DayStatus.DONE:
            raise DomainError("Bu vazifa bugun allaqachon tasdiqlangan")
        raise InvalidStateTransition(f"Bu kun uchun isbot qabul qilinmaydi ({state})")

    def note_task_approved(self, day: date, task_key: str) -> None:
        """Optional tasks never decide the day, but they are worth points."""
        if self.status is not ParticipationStatus.ACTIVE:
            return
        task = self.task(day, task_key)
        if task is not None and not task.required:
            self._record(
                OptionalTaskCompleted(
                    participation_id=self.id,
                    user_id=self.user_id,
                    day=day,
                    task_key=task.key,
                    minutes=task.minutes,
                )
            )

    def record_approved_day(self, day: date) -> None:
        """All required tasks of `day` are approved — possibly while the day is still running."""
        if self.status is not ParticipationStatus.ACTIVE:
            return
        state = self.day_status(day)
        if state is DayStatus.DONE:
            return
        if state not in (DayStatus.PENDING, DayStatus.AWAITING_REVIEW):
            raise InvalidStateTransition(f"{day} kuni allaqachon yopilgan ({state})")
        self._mark_done(day)
        self._complete_if_finished()

    def settle_day(self, day: date, evidence: DayEvidence) -> None:
        """Judge a day that is over. Idempotent (daily job, late AI or moderator decisions)."""
        if self.status is not ParticipationStatus.ACTIVE:
            return
        if self.day_status(day) not in (DayStatus.PENDING, DayStatus.AWAITING_REVIEW):
            return
        match evidence:
            case DayEvidence.APPROVED:
                self._mark_done(day)
            case DayEvidence.PENDING:
                self.days[day] = DayStatus.AWAITING_REVIEW
            case DayEvidence.AI_REJECTED if self.is_stake:
                # Fairness rule: stake money is never lost on an AI decision alone.
                self.days[day] = DayStatus.AWAITING_REVIEW
                self._record(DayNeedsHumanReview(participation_id=self.id, day=day))
            case _:
                self._miss(day)
        self._complete_if_finished()

    # --- Internals ---------------------------------------------------------------------

    def _mark_done(self, day: date) -> None:
        self.days[day] = DayStatus.DONE
        self.current_streak += 1
        self.best_streak = max(self.best_streak, self.current_streak)
        self._record(
            DayCompleted(
                participation_id=self.id,
                user_id=self.user_id,
                day=day,
                streak=self.current_streak,
                difficulty=self.difficulty,
            )
        )

    def _miss(self, day: date) -> None:
        if self.freezes_left > 0:
            self.days[day] = DayStatus.FROZEN
            self.freezes_used += 1
            self._record(DayFrozen(participation_id=self.id, user_id=self.user_id, day=day))
            return
        self.days[day] = DayStatus.MISSED
        self.current_streak = 0
        self.status = ParticipationStatus.FAILED
        self.finished_on = day
        self._record(
            ParticipationFailed(
                participation_id=self.id,
                user_id=self.user_id,
                mode=self.mode,
                stake=self.stake,
                missed_day=day,
            )
        )

    def _complete_if_finished(self) -> None:
        if self.status is not ParticipationStatus.ACTIVE:
            return
        if not all(s in (DayStatus.DONE, DayStatus.FROZEN) for s in self.days.values()):
            return
        self.status = ParticipationStatus.COMPLETED
        self.finished_on = self.end_date
        self._record(
            ParticipationCompleted(
                participation_id=self.id,
                user_id=self.user_id,
                mode=self.mode,
                stake=self.stake,
                difficulty=self.difficulty,
                duration_days=self.duration_days,
                finished_on=self.end_date,
            )
        )
