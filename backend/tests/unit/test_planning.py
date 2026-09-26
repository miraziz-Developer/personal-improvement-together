from uuid import uuid4

import pytest

from pit.modules.challenges.domain.challenge import Category
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.planning.domain.plan import (
    Availability,
    OnboardingAnswers,
    Plan,
    PlanProposal,
    PlanStatus,
)
from pit.shared.domain.errors import DomainError, InvalidStateTransition, InvariantViolation
from tests.factories import ANSWERS, AVAILABILITY


def task(key: str, minutes: int) -> TaskSpec:
    return TaskSpec(key=key, title=key.title(), minutes=minutes)


def proposal(schedule: Schedule, *, duration_days: int = 30) -> PlanProposal:
    return PlanProposal(
        title="Backend: 1-bosqich",
        description="FastAPI asoslari",
        category=Category.CODE,
        duration_days=duration_days,
        difficulty=3,
        verification_prompt="Kod yoki dars konspekti ko'rinishi kerak",
        schedule=schedule,
    )


WEEKDAY_PLAN = Schedule.by_weekday({d: [task("lesson", 90)] for d in range(5)})


def draft(schedule: Schedule = WEEKDAY_PLAN) -> Plan:
    return Plan.draft(
        plan_id=uuid4(), user_id=uuid4(), answers=ANSWERS, proposal=proposal(schedule)
    )


def test_plan_fits_within_80_percent_of_free_time() -> None:
    assert draft().status is PlanStatus.DRAFT
    with pytest.raises(DomainError, match="Dushanba: reja 100 daqiqa"):
        draft(Schedule.by_weekday({0: [task("lesson", 100)]}))


def test_no_tasks_on_a_day_without_free_time() -> None:
    with pytest.raises(DomainError, match="Yakshanba"):
        draft(Schedule.by_weekday({6: [task("lesson", 30)]}))


def test_ai_must_use_an_allowed_duration() -> None:
    with pytest.raises(InvariantViolation):
        Plan.draft(
            plan_id=uuid4(),
            user_id=uuid4(),
            answers=ANSWERS,
            proposal=proposal(WEEKDAY_PLAN, duration_days=45),
        )


def test_user_can_edit_until_the_plan_starts() -> None:
    plan = draft()
    saturday_project = Schedule.by_weekday({5: [task("project", 180)]})
    plan.edit_schedule(saturday_project)
    assert plan.challenge_spec()["default_schedule"] == saturday_project

    plan.mark_started(challenge_id=uuid4(), participation_id=uuid4())
    with pytest.raises(InvalidStateTransition):
        plan.edit_schedule(WEEKDAY_PLAN)


def test_onboarding_needs_a_goal_and_some_free_time() -> None:
    with pytest.raises(InvariantViolation):
        OnboardingAnswers(
            goal=" ", motivation="", current_level="", obstacles="", availability=AVAILABILITY
        )
    with pytest.raises(InvariantViolation):
        Availability.from_mapping({})
