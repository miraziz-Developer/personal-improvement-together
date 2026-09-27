"""Life plan: several goals in one hourly routine. Each goal still becomes its own challenge
(its own streak — skipping the run does not break the coding streak); the life plan is what
keeps them from clashing and shows them as one day."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from pit.modules.challenges.domain.challenge import ChallengeSpec
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.planning.domain.plan import (
    MAX_ANSWER_LENGTH,
    PlanProposal,
    PlanStatus,
    proposal_spec,
)
from pit.modules.planning.domain.routine import DayFrame, check_fits
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import InvalidStateTransition, InvariantViolation, NotFound

LIFE_PLAN_DURATIONS = frozenset({30, 60, 90})
MAX_GOALS = 3


@dataclass(frozen=True, slots=True)
class GoalAnswers:
    goal: str  # "Kuchli backend dasturchi bo'lish"
    motivation: str = ""
    current_level: str = ""

    def __post_init__(self) -> None:
        if len(self.goal.strip()) < 3:
            raise InvariantViolation("Har bir maqsadni yozing")
        if any(
            len(t) > MAX_ANSWER_LENGTH for t in (self.goal, self.motivation, self.current_level)
        ):
            raise InvariantViolation(f"Har bir javob {MAX_ANSWER_LENGTH} belgidan oshmasin")


@dataclass(frozen=True, slots=True)
class LifePlanRequest:
    """What the user tells us: the goals, the shape of the day and how long."""

    goals: tuple[GoalAnswers, ...]
    frame: DayFrame
    duration_days: int
    language: str = "uz"

    def __post_init__(self) -> None:
        if not 1 <= len(self.goals) <= MAX_GOALS:
            raise InvariantViolation(f"1 dan {MAX_GOALS} tagacha maqsad kiriting")
        if self.duration_days not in LIFE_PLAN_DURATIONS:
            raise InvariantViolation("Muddat 30, 60 yoki 90 kun bo'lsin")


@dataclass(frozen=True, slots=True)
class LifeGoal:
    key: str  # "g1", "g2", "g3" — stable within the plan
    answers: GoalAnswers
    proposal: PlanProposal
    challenge_id: UUID | None = None
    participation_id: UUID | None = None


@dataclass(eq=False, kw_only=True)
class LifePlan(AggregateRoot):
    user_id: UUID
    frame: DayFrame
    duration_days: int
    language: str
    goals: tuple[LifeGoal, ...]
    status: PlanStatus = PlanStatus.DRAFT

    @classmethod
    def draft(
        cls,
        *,
        plan_id: UUID,
        user_id: UUID,
        request: LifePlanRequest,
        proposals: tuple[PlanProposal, ...],
    ) -> LifePlan:
        if len(proposals) != len(request.goals):
            raise InvariantViolation("Har bir maqsad uchun reja bo'lishi kerak")
        goals = tuple(
            LifeGoal(
                key=f"g{index + 1}",
                answers=answers,
                proposal=replace(proposal, duration_days=request.duration_days),
            )
            for index, (answers, proposal) in enumerate(zip(request.goals, proposals, strict=True))
        )
        check_fits(request.frame, [g.proposal.schedule for g in goals])
        return cls(
            id=plan_id,
            user_id=user_id,
            frame=request.frame,
            duration_days=request.duration_days,
            language=request.language,
            goals=goals,
        )

    def goal(self, key: str) -> LifeGoal:
        found = next((g for g in self.goals if g.key == key), None)
        if found is None:
            raise NotFound("Bu maqsad rejada yo'q")
        return found

    def edit_goal_schedule(self, key: str, schedule: Schedule) -> None:
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Boshlangan rejani challenge sahifasida o'zgartiring")
        self.goal(key)
        goals = tuple(
            replace(g, proposal=replace(g.proposal, schedule=schedule)) if g.key == key else g
            for g in self.goals
        )
        check_fits(self.frame, [g.proposal.schedule for g in goals])
        self.goals = goals

    def challenge_spec(self, key: str) -> ChallengeSpec:
        return proposal_spec(self.goal(key).proposal)

    def mark_started(self, started: dict[str, tuple[UUID, UUID]]) -> None:
        """started: goal key -> (challenge id, participation id)."""
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Bu reja allaqachon boshlangan")
        if started.keys() != {g.key for g in self.goals}:
            raise InvariantViolation("Hamma maqsadlar birga boshlanadi")
        self.goals = tuple(
            replace(g, challenge_id=started[g.key][0], participation_id=started[g.key][1])
            for g in self.goals
        )
        self.status = PlanStatus.STARTED
