"""Life plan: several goals in one hourly routine. Each goal still becomes its own challenge
(its own streak — skipping the run does not break the coding streak); the life plan is what
keeps them from clashing and shows them as one day."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from pit.modules.challenges.domain.challenge import Category, ChallengeSpec
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.planning.domain.plan import (
    MAX_ANSWER_LENGTH,
    PlanProposal,
    PlanStatus,
    proposal_spec,
)
from pit.modules.planning.domain.routine import DayFrame, check_fits, pack
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
class ExistingRun:
    """A challenge the user is already on. The routine gives its tasks clock times — it never
    changes what the challenge asks for."""

    participation_id: UUID
    challenge_id: UUID
    title: str
    category: Category
    schedule: Schedule


@dataclass(frozen=True, slots=True)
class LifePlanRequest:
    """What the user tells us: new goals, running challenges, the shape of the day, how long."""

    goals: tuple[GoalAnswers, ...]
    frame: DayFrame
    duration_days: int
    language: str = "uz"
    existing: tuple[ExistingRun, ...] = ()

    def __post_init__(self) -> None:
        if len(self.goals) > MAX_GOALS:
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
    existing: tuple[ExistingRun, ...] = ()
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
        if not request.goals and not request.existing:
            raise InvariantViolation("1 dan 3 tagacha maqsad kiriting")
        # Running challenges go first and only get times; new goals fit around them.
        fixed = len(request.existing)
        packed = pack(
            request.frame,
            [e.schedule for e in request.existing] + [p.schedule for p in proposals],
            fixed=fixed,
        )
        existing = tuple(
            replace(run, schedule=schedule)
            for run, schedule in zip(request.existing, packed[:fixed], strict=True)
        )
        goals = tuple(
            LifeGoal(
                key=f"g{index + 1}",
                answers=answers,
                proposal=replace(proposal, duration_days=request.duration_days, schedule=schedule),
            )
            for index, (answers, proposal, schedule) in enumerate(
                zip(request.goals, proposals, packed[fixed:], strict=True)
            )
        )
        plan = cls(
            id=plan_id,
            user_id=user_id,
            frame=request.frame,
            duration_days=request.duration_days,
            language=request.language,
            goals=goals,
            existing=existing,
        )
        plan._check()
        return plan

    def _schedules(self) -> list[Schedule]:
        return [e.schedule for e in self.existing] + [g.proposal.schedule for g in self.goals]

    def _check(self) -> None:
        check_fits(self.frame, self._schedules(), fixed=len(self.existing))

    def goal(self, key: str) -> LifeGoal:
        found = next((g for g in self.goals if g.key == key), None)
        if found is None:
            raise NotFound("Bu maqsad rejada yo'q")
        return found

    def edit_goal_schedule(self, key: str, schedule: Schedule) -> None:
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Boshlangan rejani challenge sahifasida o'zgartiring")
        self.goal(key)
        previous = self.goals
        self.goals = tuple(
            replace(g, proposal=replace(g.proposal, schedule=schedule)) if g.key == key else g
            for g in self.goals
        )
        try:
            self._check()
        except Exception:
            self.goals = previous
            raise

    def retime_existing(self, participation_id: UUID, schedule: Schedule) -> None:
        """New times for a running challenge's tasks (its tasks themselves stay as they are)."""
        if self.status is not PlanStatus.DRAFT:
            raise InvalidStateTransition("Boshlangan rejani challenge sahifasida o'zgartiring")
        run = next((e for e in self.existing if e.participation_id == participation_id), None)
        if run is None:
            raise NotFound("Bu challenge kun tartibida yo'q")
        if schedule.without_times() != run.schedule.without_times():
            raise InvariantViolation("Kun tartibida faqat vazifalar vaqtini o'zgartirish mumkin")
        previous = self.existing
        self.existing = tuple(
            replace(e, schedule=schedule) if e.participation_id == participation_id else e
            for e in self.existing
        )
        try:
            self._check()
        except Exception:
            self.existing = previous
            raise

    def change_frame(self, frame: DayFrame) -> None:
        """New wake/sleep times or commitments for the routine being lived. The caller checks
        the running tasks against it (they live in the participations, not here)."""
        if self.status is PlanStatus.REPLACED:
            raise InvalidStateTransition("Bu kun tartibi yangisi bilan almashtirilgan")
        self.frame = frame

    def retire(self) -> None:
        """A newer routine replaces this one: a person lives by one daily routine."""
        if self.status is PlanStatus.STARTED:
            self.status = PlanStatus.REPLACED

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
