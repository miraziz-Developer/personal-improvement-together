from dataclasses import dataclass
from datetime import date
from uuid import UUID

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.planning.domain.life_plan import LifePlanRequest
from pit.modules.planning.domain.plan import OnboardingAnswers
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
    """Several goals + the shape of the day → one clash-free hourly routine (a draft)."""

    user_id: UUID
    request: LifePlanRequest


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
