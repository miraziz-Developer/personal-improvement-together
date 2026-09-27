"""Onboarding → AI plan → accepted plan becomes the user's personal challenge."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID

from pit.modules.challenges.domain.challenge import (
    ALLOWED_DURATIONS,
    Category,
    ChallengeSpec,
    ProofType,
    StakePolicy,
)
from pit.modules.challenges.domain.roadmap import Roadmap
from pit.modules.challenges.domain.schedule import WEEKDAY_NAMES, Schedule
from pit.modules.planning.domain.events import PlanDrafted, PlanStarted
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvalidStateTransition, InvariantViolation

# A plan may fill at most 80% of the free time the user reported: life happens, and one
# busy evening should not break a streak.
LOAD_FACTOR = 0.8
MAX_FREE_MINUTES_PER_DAY = 16 * 60
MAX_ANSWER_LENGTH = 500
PLAN_PROOF_TYPES = frozenset({ProofType.PHOTO, ProofType.TEXT})


@dataclass(frozen=True, slots=True)
class Availability:
    minutes_by_weekday: tuple[int, ...]  # index 0 = Monday

    def __post_init__(self) -> None:
        if len(self.minutes_by_weekday) != 7:
            raise InvariantViolation("Bo'sh vaqt 7 kun uchun ko'rsatilishi kerak")
        if any(not 0 <= m <= MAX_FREE_MINUTES_PER_DAY for m in self.minutes_by_weekday):
            raise InvariantViolation("Kunlik bo'sh vaqt 0 dan 16 soatgacha bo'lishi kerak")
        if not any(self.minutes_by_weekday):
            raise InvariantViolation("Haftada kamida bir kun bo'sh vaqt ko'rsating")

    @classmethod
    def from_mapping(cls, minutes: Mapping[int, int]) -> Availability:
        return cls(minutes_by_weekday=tuple(minutes.get(weekday, 0) for weekday in range(7)))

    def budget(self, weekday: int) -> int:
        return int(self.minutes_by_weekday[weekday] * LOAD_FACTOR)


@dataclass(frozen=True, slots=True)
class OnboardingAnswers:
    goal: str  # "3 oyda backend dasturchi bo'lish"
    motivation: str  # "Yaxshi ishga kirish"
    current_level: str  # "Python asoslarini bilaman"
    obstacles: str  # "Ish, charchoq"
    availability: Availability
    language: str = "uz"  # the plan is written in it: "uz" | "ru"

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise InvariantViolation("Maqsadingizni yozing")
        texts = (self.goal, self.motivation, self.current_level, self.obstacles)
        if any(len(t) > MAX_ANSWER_LENGTH for t in texts):
            raise InvariantViolation(f"Har bir javob {MAX_ANSWER_LENGTH} belgidan oshmasin")


@dataclass(frozen=True, slots=True)
class PlanProposal:
    """What the AI suggests. The user may edit the schedule before starting."""

    title: str
    description: str
    category: Category
    duration_days: int
    difficulty: int
    verification_prompt: str
    schedule: Schedule
    roadmap: Roadmap | None = None  # week themes and day lessons; the AI writes them


def proposal_spec(p: PlanProposal) -> ChallengeSpec:
    """What an accepted proposal becomes: the user's personal challenge."""
    return ChallengeSpec(
        title=p.title,
        description=p.description,
        category=p.category,
        duration_days=p.duration_days,
        difficulty=p.difficulty,
        proof_types=PLAN_PROOF_TYPES,
        verification_prompt=p.verification_prompt,
        stake_policy=StakePolicy(allowed=True),
        default_schedule=p.schedule,
        roadmap=p.roadmap,
    )


class PlanStatus(StrEnum):
    DRAFT = "draft"
    STARTED = "started"


def ensure_fits(schedule: Schedule, availability: Availability) -> None:
    for weekday, name in enumerate(WEEKDAY_NAMES):
        planned = schedule.minutes_on_weekday(weekday)
        budget = availability.budget(weekday)
        if planned > budget:
            raise DomainError(
                f"{name}: reja {planned} daqiqa, bo'sh vaqtingizning 80% i esa {budget} daqiqa"
            )


@dataclass(eq=False, kw_only=True)
class Plan(AggregateRoot):
    user_id: UUID
    answers: OnboardingAnswers
    proposal: PlanProposal
    status: PlanStatus = PlanStatus.DRAFT
    challenge_id: UUID | None = None
    participation_id: UUID | None = None

    @classmethod
    def draft(
        cls, *, plan_id: UUID, user_id: UUID, answers: OnboardingAnswers, proposal: PlanProposal
    ) -> Plan:
        if proposal.duration_days not in ALLOWED_DURATIONS:
            raise InvariantViolation(f"Reja davomiyligi {sorted(ALLOWED_DURATIONS)} dan biri")
        ensure_fits(proposal.schedule, answers.availability)
        plan = cls(id=plan_id, user_id=user_id, answers=answers, proposal=proposal)
        plan._record(PlanDrafted(plan_id=plan_id, user_id=user_id))
        return plan

    def edit_schedule(self, schedule: Schedule) -> None:
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Boshlangan rejani challenge sahifasida o'zgartiring")
        ensure_fits(schedule, self.answers.availability)
        self.proposal = replace(self.proposal, schedule=schedule)

    def challenge_spec(self) -> ChallengeSpec:
        return proposal_spec(self.proposal)

    def mark_started(self, *, challenge_id: UUID, participation_id: UUID) -> None:
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Bu reja allaqachon boshlangan")
        self.status = PlanStatus.STARTED
        self.challenge_id = challenge_id
        self.participation_id = participation_id
        self._record(
            PlanStarted(plan_id=self.id, user_id=self.user_id, participation_id=participation_id)
        )
