import json
from datetime import date, time, timedelta

import pytest

from pit.modules.challenges.domain.roadmap import Milestone, Roadmap
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.challenges.infrastructure.serialization import (
    roadmap_from_json,
    roadmap_to_json,
    schedule_from_json,
    schedule_to_json,
)
from pit.modules.planning.domain.plan import Availability, OnboardingAnswers
from pit.modules.planning.infrastructure.generators import LlmPlanGenerator, template_roadmap
from pit.shared.domain.errors import InvariantViolation

START = date(2026, 10, 1)  # a Thursday
ROADMAP = Roadmap(
    outcome="Python'da kichik loyiha",
    weeks=(
        Milestone("Asoslar", "Til asoslari", ("O'zgaruvchilar", "Shartlar", "Sikllar")),
        Milestone("Git", "Versiyalar", ("Commit",)),
    ),
)


def working(days: int, *, skip_weekday: int | None = None) -> list[date]:
    all_days = [START + timedelta(days=i) for i in range(days)]
    return [d for d in all_days if d.weekday() != skip_weekday]


def test_each_working_day_gets_the_next_lesson() -> None:
    days = working(14, skip_weekday=6)  # Sundays off
    lessons = [ROADMAP.focus(START, days, d) for d in days[:4]]
    assert [f.lesson for f in lessons if f] == ["O'zgaruvchilar", "Shartlar", "Sikllar", None]
    # Sunday is a rest day, so the 3rd lesson lands on Saturday and Monday is the 4th working day
    assert days[2].weekday() == 5 and days[3].weekday() == 0
    rest = ROADMAP.focus(START, days, START + timedelta(days=3))
    assert rest is not None and (rest.theme, rest.lesson) == ("Asoslar", None)


def test_weeks_count_from_the_start_and_the_last_one_continues() -> None:
    days = working(30)
    second = ROADMAP.focus(START, days, START + timedelta(days=7))
    assert second is not None and (second.week, second.theme, second.lesson) == (2, "Git", "Commit")
    later = ROADMAP.focus(START, days, START + timedelta(days=20))
    assert later is not None and (later.week, later.weeks, later.lesson) == (2, 2, None)
    assert ROADMAP.focus(START, days, START - timedelta(days=1)) is None


def test_a_roadmap_needs_real_content() -> None:
    with pytest.raises(InvariantViolation):
        Roadmap(outcome="x", weeks=())
    with pytest.raises(InvariantViolation):
        Milestone(" ", "goal")


def test_times_and_roadmaps_survive_storage() -> None:
    schedule = Schedule.every_day(
        TaskSpec("run", "Yugurish", 30, at=time(7, 0)), TaskSpec("read", "O'qish", 20)
    )
    restored = schedule_from_json(json.loads(json.dumps(schedule_to_json(schedule))))
    assert restored == schedule and restored.week[0][0].at == time(7, 0)
    assert roadmap_from_json(json.loads(json.dumps(roadmap_to_json(ROADMAP)))) == ROADMAP
    assert roadmap_from_json(None) is None


ANSWERS = OnboardingAnswers(
    goal="Python",
    motivation="",
    current_level="",
    obstacles="",
    availability=Availability(minutes_by_weekday=(90,) * 7),
)


def ai_answer(roadmap: object) -> dict[str, object]:
    return {
        "title": "Python yo'li",
        "description": "30 kun",
        "category": "code",
        "duration_days": 30,
        "difficulty": 3,
        "verification_prompt": "Ekranda kod",
        "roadmap": roadmap,
        "week": [[{"key": "code", "title": "Kod", "minutes": 45, "required": True, "at": "19:30"}]]
        * 7,
    }


def test_the_ai_plan_keeps_times_and_roadmap() -> None:
    roadmap = {
        "outcome": "Loyiha",
        "weeks": [{"theme": "Asoslar", "goal": "Asos", "lessons": ["A", "B"]}],
    }
    proposal = LlmPlanGenerator._to_proposal(ai_answer(roadmap), ANSWERS)
    assert proposal.schedule.week[0][0].at == time(19, 30)
    assert proposal.roadmap is not None and proposal.roadmap.weeks[0].lessons == ("A", "B")


def test_a_broken_ai_roadmap_is_dropped_not_the_plan() -> None:
    proposal = LlmPlanGenerator._to_proposal(ai_answer({"outcome": "", "weeks": []}), ANSWERS)
    assert proposal.roadmap is None and proposal.title == "Python yo'li"


def test_the_template_roadmap_covers_every_week() -> None:
    assert len(template_roadmap("Python", 30, ru=False).weeks) == 5
    assert template_roadmap("Python", 21, ru=True).weeks[0].theme == "Фундамент"


def test_month_milestones_lose_the_numbers_the_app_adds_itself() -> None:
    roadmap = {
        "outcome": "Loyiha",
        "months": ["1-oy: Asoslar", "2-oy — Loyiha", "Deploy"],
        "weeks": [{"theme": "Asoslar", "goal": "Asos", "lessons": ["A"]}],
    }
    proposal = LlmPlanGenerator._to_proposal(ai_answer(roadmap), ANSWERS)
    assert proposal.roadmap is not None and proposal.roadmap.months == (
        "Asoslar",
        "Loyiha",
        "Deploy",
    )
