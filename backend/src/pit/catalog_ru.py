"""Russian texts for the ready-made challenges. The catalog is stored in Uzbek; the API swaps
these in for readers who asked for Russian. Keyed by the stable catalog id, tasks by task key."""

from dataclasses import dataclass, field
from uuid import UUID

from pit.catalog import catalog_id


@dataclass(frozen=True, slots=True)
class CatalogText:
    title: str
    description: str
    tasks: dict[str, str] = field(default_factory=dict)


CATALOG_RU: dict[UUID, CatalogText] = {
    catalog_id("sport-21"): CatalogText(
        "21 день спорта",
        "Тренировки 6 дней в неделю: зал, бег или дома. 21 день — первый этап "
        "формирования новой привычки.",
        {"workout": "Тренировка", "stretch": "Растяжка"},
    ),
    catalog_id("reading-30"): CatalogText(
        "Книга каждый день",
        "Каждый день минимум 20 страниц. За месяц — 1-2 прочитанные книги, "
        "а к концу года — целая полка.",
        {"read": "Прочитать 20 страниц", "notes": "Выводы из прочитанного"},
    ),
    catalog_id("code-30"): CatalogText(
        "30-дневный марафон кода",
        "По будням пишем код, в субботу — личный проект. За месяц появится работа для портфолио.",
        {"code": "Писать код", "read": "Прочитать техническую статью", "project": "Личный проект"},
    ),
    catalog_id("english-30"): CatalogText(
        "Английский: 30 дней",
        "Каждый день 10 новых слов и урок. Воскресенье — повторение недели. "
        "К концу месяца — 250+ новых слов.",
        {"words": "10 новых слов", "lesson": "Урок", "review": "Повторение недели"},
    ),
    catalog_id("early-21"): CatalogText(
        "Ранний подъём: 21 день",
        "Вставать до 06:30 и начинать день с плана. Раннее утро — самый продуктивный час дня.",
        {"wake": "Подъём до 06:30", "plan": "Записать план дня"},
    ),
    catalog_id("meditation-14"): CatalogText(
        "14 дней внутреннего спокойствия",
        "Каждый день 10 минут медитации или дыхательных упражнений. Маленький шаг — "
        "большое спокойствие.",
        {"meditate": "10 минут медитации"},
    ),
    catalog_id("steps-30"): CatalogText(
        "10 000 шагов в день",
        "Простая, но сильная привычка: 10 000 шагов каждый день. Самая лёгкая инвестиция "
        "в сердце, настроение и сон.",
        {"steps": "10 000 шагов"},
    ),
    catalog_id("muaythai-30"): CatalogText(
        "Муай-тай: 30 дней",
        "4 тренировки и 2 лёгкие пробежки в неделю. Сила, выносливость и дисциплина — за месяц.",
        {"training": "Тренировка по муай-тай", "run": "Лёгкая пробежка"},
    ),
}

_TEXTS: dict[str, dict[UUID, CatalogText]] = {"ru": CATALOG_RU}


def catalog_text(challenge_id: UUID, locale: str) -> CatalogText | None:
    """The translated texts of a catalog challenge, or None to keep the stored (Uzbek) ones."""
    return _TEXTS.get(locale, {}).get(challenge_id)
