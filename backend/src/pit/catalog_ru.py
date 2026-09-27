"""Russian texts for the ready-made challenges. The catalog is stored in Uzbek; the API swaps
these in for readers who asked for Russian. Keyed by the stable catalog id, tasks by task key."""

from dataclasses import dataclass, field
from uuid import UUID

from pit.catalog import catalog_id
from pit.catalog_roadmaps_ru import ROADMAPS_RU
from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.challenges.domain.roadmap import Roadmap
from pit.modules.challenges.domain.schedule import TaskSpec


@dataclass(frozen=True, slots=True)
class CatalogText:
    title: str
    description: str
    tasks: dict[str, str] = field(default_factory=dict)
    roadmap: Roadmap | None = None


CATALOG_RU: dict[UUID, CatalogText] = {
    catalog_id("sport-21"): CatalogText(
        "21 день спорта",
        "Тренировки 6 дней в неделю: зал, бег или дома. 21 день — первый этап "
        "формирования новой привычки.",
        {"workout": "Тренировка", "stretch": "Растяжка"},
        ROADMAPS_RU["sport-21"],
    ),
    catalog_id("reading-30"): CatalogText(
        "Книга каждый день",
        "Каждый день минимум 20 страниц. За месяц — 1-2 прочитанные книги, "
        "а к концу года — целая полка.",
        {"read": "Прочитать 20 страниц", "notes": "Выводы из прочитанного"},
        ROADMAPS_RU["reading-30"],
    ),
    catalog_id("code-30"): CatalogText(
        "30-дневный марафон кода",
        "6 дней в неделю: каждый день новая тема, каждую неделю — применение в проекте. "
        "За месяц появится работа для портфолио.",
        {"code": "Писать код", "read": "Прочитать техническую статью"},
        ROADMAPS_RU["code-30"],
    ),
    catalog_id("english-30"): CatalogText(
        "Английский: 30 дней",
        "Каждый день 10 новых слов и новая тема, в конце недели — повторение. "
        "К концу месяца — 250+ новых слов.",
        {"words": "10 новых слов", "lesson": "Урок"},
        ROADMAPS_RU["english-30"],
    ),
    catalog_id("early-21"): CatalogText(
        "Ранний подъём: 21 день",
        "Вставать до 06:30 и начинать день с плана. Раннее утро — самый продуктивный час дня.",
        {"wake": "Подъём до 06:30", "plan": "Записать план дня"},
        ROADMAPS_RU["early-21"],
    ),
    catalog_id("meditation-14"): CatalogText(
        "14 дней внутреннего спокойствия",
        "Каждый день 10 минут медитации или дыхательных упражнений. Маленький шаг — "
        "большое спокойствие.",
        {"meditate": "10 минут медитации"},
        ROADMAPS_RU["meditation-14"],
    ),
    catalog_id("steps-30"): CatalogText(
        "10 000 шагов в день",
        "Простая, но сильная привычка: 10 000 шагов каждый день. Самая лёгкая инвестиция "
        "в сердце, настроение и сон.",
        {"steps": "10 000 шагов"},
        ROADMAPS_RU["steps-30"],
    ),
    catalog_id("muaythai-30"): CatalogText(
        "Муай-тай: 30 дней",
        "6 дней в неделю: техника, бег и функционалка по очереди. Сила, выносливость "
        "и дисциплина — за месяц.",
        {"training": "Тренировка"},
        ROADMAPS_RU["muaythai-30"],
    ),
}

_TEXTS: dict[str, dict[UUID, CatalogText]] = {"ru": CATALOG_RU}


class CatalogTexts:
    """The coach's view of the catalog translations (see coaching.application.ports)."""

    def title(self, challenge: Challenge, locale: str) -> str:
        text = catalog_text(challenge.id, locale)
        return text.title if text else challenge.title

    def roadmap(self, challenge: Challenge, locale: str) -> Roadmap | None:
        text = catalog_text(challenge.id, locale)
        return text.roadmap if text and text.roadmap else challenge.roadmap

    def task_title(self, challenge: Challenge, task: TaskSpec, locale: str) -> str:
        text = catalog_text(challenge.id, locale)
        return text.tasks.get(task.key, task.title) if text else task.title


def catalog_text(challenge_id: UUID, locale: str) -> CatalogText | None:
    """The translated texts of a catalog challenge, or None to keep the stored (Uzbek) ones."""
    return _TEXTS.get(locale, {}).get(challenge_id)
