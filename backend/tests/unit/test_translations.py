"""Every translated text set must cover what it translates — a missing entry would quietly
show Uzbek in the middle of a Russian page."""

from pit.catalog import build_catalog
from pit.catalog_ru import CATALOG_RU
from pit.modules.planning.infrastructure.generators import PLAN_LANGUAGE, PLAN_PROMPT, PROFILES
from pit.modules.planning.infrastructure.generators_ru import PROFILES_RU
from pit.modules.ranking.domain.achievements import BADGES
from pit.modules.ranking.domain.achievements_ru import BADGES_RU


def test_every_catalog_challenge_and_task_has_russian_texts() -> None:
    for challenge in build_catalog():
        text = CATALOG_RU[challenge.id]
        keys = {task.key for day in challenge.default_schedule.week for task in day}
        assert keys <= text.tasks.keys(), challenge.title


def test_every_badge_has_russian_texts() -> None:
    assert {badge.key for badge in BADGES} == BADGES_RU.keys()


def test_template_plans_have_russian_profiles() -> None:
    assert PROFILES.keys() == PROFILES_RU.keys()


def test_plan_prompt_names_the_language() -> None:
    assert "rus tilida" in PLAN_PROMPT.format(language=PLAN_LANGUAGE["ru"])
