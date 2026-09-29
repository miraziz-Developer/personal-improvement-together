from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, time
from uuid import UUID

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.planning.domain.life_plan import LifePlanRequest
from pit.modules.planning.domain.plan import OnboardingAnswers
from pit.modules.planning.domain.routine import DayFrame
from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class DraftPlan(Command):
    """The "make me a plan" path: onboarding answers → AI proposal (a draft)."""

    user_id: UUID
    answers: OnboardingAnswers


@dataclass(frozen=True, kw_only=True)
class EditPlan(Command):
    user_id: UUID
    plan_id: UUID
    schedule: Schedule


@dataclass(frozen=True, kw_only=True)
class StartPlan(Command):
    user_id: UUID
    plan_id: UUID
    mode: ParticipationMode
    stake_amount: int = 0
    start_date: date | None = None


@dataclass(frozen=True, kw_only=True)
class DraftLifePlan(Command):
    """Several goals + the shape of the day → one clash-free hourly routine (a draft).
    Every challenge the user is already on joins the routine too; `times` holds the clock
    times the user chose for their tasks (participation id -> task key -> time, None = any)."""

    user_id: UUID
    request: LifePlanRequest
    times: Mapping[UUID, Mapping[str, time | None]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class RetimeLifePlanRun(Command):
    user_id: UUID
    plan_id: UUID
    participation_id: UUID
    schedule: Schedule


@dataclass(frozen=True, kw_only=True)
class EditLifePlanGoal(Command):
    user_id: UUID
    plan_id: UUID
    goal_key: str
    schedule: Schedule


@dataclass(frozen=True, kw_only=True)
class StartLifePlan(Command):
    """Every goal becomes its own challenge and participation (free mode), in one go."""

    user_id: UUID
    plan_id: UUID


@dataclass(frozen=True, kw_only=True)
class RetimeTasks(Command):
    """Move tasks of a running challenge on the daily timeline (task key -> time, None = no
    time). The same time applies on every day the task happens."""

    user_id: UUID
    participation_id: UUID
    times: Mapping[str, time | None]


@dataclass(frozen=True, kw_only=True)
class ChangeDayFrame(Command):
    """New wake/sleep times or fixed commitments for the routine the user lives by."""

    user_id: UUID
    frame: DayFrame


@dataclass(frozen=True, kw_only=True)
class AddToRoutine(Command):
    """Join a challenge straight into the daily routine: "I'll do this at that time".
    times: task key -> time; a missing or None time is placed in the free time for you."""

    user_id: UUID
    challenge_id: UUID
    times: Mapping[str, time | None] = field(default_factory=dict)
