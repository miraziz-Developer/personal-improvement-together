"""Plan generators. The AI writes the plan; the template generator is both the no-AI mode
and the safety net when the AI fails. Either way the result is fitted to the user's time."""

import json
import logging
import math
import re
from dataclasses import replace
from datetime import time
from typing import Any

from pit.modules.challenges.domain.challenge import ALLOWED_DURATIONS, Category
from pit.modules.challenges.domain.roadmap import MAX_TEXT, MAX_WEEKS, Milestone, Roadmap
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.planning.domain.plan import OnboardingAnswers, PlanProposal
from pit.modules.planning.infrastructure.generators_ru import (
    DESCRIPTION_RU,
    KEYWORDS_RU,
    PROFILES_RU,
    STAGES_RU,
    TITLE_RU,
)
from pit.shared.domain.errors import DomainError
from pit.shared.infrastructure.llm import LlmPool

logger = logging.getLogger(__name__)

MIN_TASK_MINUTES = 15

# category -> (main task, its minutes, optional extra task, what a valid proof shows)
PROFILES: dict[Category, tuple[str, int, str, str]] = {
    Category.SPORT: (
        "Mashg'ulot",
        45,
        "Cho'zilish va tiklanish",
        "Rasmda mashq qilayotgan foydalanuvchi, sport zali yoki mashq jihozlari ko'rinsin.",
    ),
    Category.CODE: (
        "Kod yozish",
        60,
        "Texnik maqola yoki hujjat o'qish",
        "Rasmda ekrandagi kod muharriri yoki terminal ko'rinsin (skrinshot emas, ekran fotosi).",
    ),
    Category.READING: (
        "Kitob o'qish",
        30,
        "O'qilganlar bo'yicha qisqa xulosa",
        "Rasmda ochiq kitob sahifasi ko'rinsin, matnda o'qilgan qism haqida xulosa bo'lsin.",
    ),
    Category.STUDY: (
        "Dars va mashq",
        45,
        "O'tilganni takrorlash",
        "Rasmda daftar, darslik yoki o'quv ilovasi ko'rinsin, matnda nima o'rganilgani yozilsin.",
    ),
    Category.HEALTH: (
        "Sog'lom odat",
        20,
        "Kun xulosasi",
        "Rasm yoki matn bajarilgan sog'lom odatni aniq ko'rsatsin.",
    ),
    Category.CUSTOM: (
        "Asosiy vazifa",
        40,
        "Kun xulosasi",
        "Isbot maqsadga oid bugun bajarilgan ishni aniq ko'rsatsin.",
    ),
}

KEYWORDS: tuple[tuple[Category, tuple[str, ...]], ...] = (
    (Category.READING, ("kitob", "roman", "mutolaa")),
    (Category.CODE, ("kod", "dastur", "python", "backend", "frontend", "developer", "program")),
    (Category.SPORT, ("sport", "zal", "yugur", "fitnes", "muay", "boks", "vazn", "mashq", "suz")),
    (Category.STUDY, ("ingliz", "til", "ielts", "imtihon", "o'rgan", "matem", "fizika", "sat")),
    (Category.HEALTH, ("uyqu", "suv ich", "meditat", "sog'lom", "ovqat", "erta tur")),
)


def guess_category(text: str) -> Category:
    lowered = text.lower()
    for category, words in KEYWORDS:
        if any(word in lowered for word in (*words, *KEYWORDS_RU.get(category, ()))):
            return category
    return Category.CUSTOM


def fit_to_availability(schedule: Schedule, answers: OnboardingAnswers) -> Schedule:
    """Shrink a day that is too full; drop days with no free time. Never grows the plan."""
    week: list[tuple[TaskSpec, ...]] = []
    for weekday, tasks in enumerate(schedule.week):
        budget = answers.availability.budget(weekday)
        if budget < MIN_TASK_MINUTES or not tasks:
            week.append(())
            continue
        total = sum(t.minutes for t in tasks)
        if total > budget:
            required = [t for t in tasks if t.required] or [tasks[0]]
            scale = budget / sum(t.minutes for t in required)
            tasks = tuple(
                replace(t, minutes=max(5, int(t.minutes * min(scale, 1) // 5 * 5)), required=True)
                for t in required
            )
        week.append(tuple(tasks))
    if not any(week):
        raise DomainError("Bo'sh vaqt juda kam: kamida bir kunga 20 daqiqa ajrating")
    return Schedule(week=tuple(week))


def _difficulty(weekly_minutes: int) -> int:
    for limit, level in ((120, 1), (240, 2), (420, 3), (600, 4)):
        if weekly_minutes < limit:
            return level
    return 5


class TemplatePlanGenerator:
    async def propose(self, answers: OnboardingAnswers) -> PlanProposal:
        category = guess_category(f"{answers.goal} {answers.motivation}")
        main_title, main_minutes, extra_title, criteria = PROFILES[category]
        ru = answers.language == "ru"
        if ru:
            main_title, extra_title, criteria = PROFILES_RU[category]
        week: list[tuple[TaskSpec, ...]] = []
        for weekday in range(7):
            budget = answers.availability.budget(weekday)
            if budget < MIN_TASK_MINUTES:
                week.append(())
                continue
            minutes = max(MIN_TASK_MINUTES, min(main_minutes, budget) // 5 * 5)
            tasks = [TaskSpec(key="main", title=main_title, minutes=minutes)]
            if budget - minutes >= MIN_TASK_MINUTES:
                tasks.append(TaskSpec(key="extra", title=extra_title, minutes=15, required=False))
            week.append(tuple(tasks))
        if not any(week):
            raise DomainError("Bo'sh vaqt juda kam: kamida bir kunga 20 daqiqa ajrating")
        schedule = Schedule(week=tuple(week))
        goal = answers.goal.strip()
        motivation, level = answers.motivation or "—", answers.current_level or "—"
        facts = {"goal": goal, "motivation": motivation, "level": level}
        return PlanProposal(
            title=(TITLE_RU if ru else "{goal} — birinchi bosqich").format(goal=goal[:80]),
            description=(
                DESCRIPTION_RU
                if ru
                else "Maqsad: {goal}. Sabab: {motivation}. Hozirgi daraja: {level}."
            ).format(**facts),
            category=category,
            duration_days=21 if category is Category.HEALTH else 30,
            difficulty=_difficulty(schedule.required_minutes_per_week),
            verification_prompt=criteria,
            schedule=schedule,
            roadmap=template_roadmap(goal, 21 if category is Category.HEALTH else 30, ru=ru),
        )


# Without the AI there are no real lessons to write, but the weeks can still climb.
STAGES_UZ = (
    ("Poydevor", "Har kuni rejaga amal qilish odatga aylanadi"),
    ("Chuqurlashtirish", "Vazifalarni ishonch bilan, kamroq kuch sarflab bajarasiz"),
    ("Qiyinlashtirish", "O'zingizni avvalgidan kattaroq vazifada sinab ko'rasiz"),
    ("Mustahkamlash", "Natijani mustahkamlaysiz va keyingi bosqichni rejalashtirasiz"),
)


def template_roadmap(goal: str, duration_days: int, *, ru: bool) -> Roadmap:
    stages = STAGES_RU if ru else STAGES_UZ
    weeks = math.ceil(duration_days / 7)
    return Roadmap(
        outcome=goal[:MAX_TEXT],
        weeks=tuple(
            Milestone(
                theme=stages[min(i, len(stages) - 1)][0], goal=stages[min(i, len(stages) - 1)][1]
            )
            for i in range(weeks)
        ),
    )


PLAN_PROMPT = """Siz shaxsiy rivojlanish murabbiyisiz. Foydalanuvchi javoblari asosida
birinchi bosqich uchun real, bajariladigan haftalik reja tuzing.
Qoidalar:
- Har hafta kuni uchun berilgan daqiqa budjetidan oshmang; budjet 0 bo'lsa — dam olish kuni.
- Har ish kunida 1-3 ta vazifa; kamida bittasi required=true.
- Vazifa nomi aniq va o'lchanadigan bo'lsin ("20 bet o'qish", "1 ta endpoint yozish").
- key: kichik lotin harflari, raqam, '-' yoki '_' (masalan "lesson", "practice").
- verification_prompt: rasm/matn isbotida nima ko'rinishi kerakligi, 1-2 gap.
- at: vazifa boshlanadigan vaqt "HH:MM" (masalan sport ertalab, o'qish kechqurun); bilmasangiz "".
- roadmap — reja qotib qolmasin, har kuni oldinga siljisin:
  - weeks: davomiylik / 7 (yuqoriga yaxlitlab) ta hafta, har biri — mavzu (theme, qisqa),
    hafta oxirida nimaga erishiladi (goal).
  - lessons: shu haftaning har bir ish kuni uchun bittadan aniq, o'lchanadigan kunlik mavzu,
    ish kunlari tartibida; har kuni oldingisidan davom etadi va takrorlanmaydi
    (masalan "Python: o'zgaruvchilar va turlar", keyingi kun "Python: if/else va sikllar").
    Darsga "Kun 1:" yoki "1-dars" kabi raqam qo'shmang — tartibni ilova o'zi ko'rsatadi.
  - outcome: oxirgi kuni foydalanuvchi nimani qila oladi, 1 gap.
- Hamma matnlar {language}."""

# How the prompt names the language the plan must be written in.
PLAN_LANGUAGE = {"uz": "o'zbek tilida (lotin)", "ru": "rus tilida (kirill)"}

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "category": {"type": "string", "enum": [c.value for c in Category]},
        "duration_days": {"type": "integer", "enum": sorted(ALLOWED_DURATIONS)},
        "difficulty": {"type": "integer"},
        "verification_prompt": {"type": "string"},
        "roadmap": {
            "type": "object",
            "properties": {
                "outcome": {"type": "string"},
                "weeks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {"type": "string"},
                            "goal": {"type": "string"},
                            "lessons": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["theme", "goal", "lessons"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["outcome", "weeks"],
            "additionalProperties": False,
        },
        "week": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "title": {"type": "string"},
                        "minutes": {"type": "integer"},
                        "required": {"type": "boolean"},
                        "at": {"type": "string"},
                    },
                    "required": ["key", "title", "minutes", "required", "at"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "required": [
        "roadmap",
        "title",
        "description",
        "category",
        "duration_days",
        "difficulty",
        "verification_prompt",
        "week",
    ],
    "additionalProperties": False,
}


def _clean_time(value: str) -> time | None:
    try:
        return time.fromisoformat(value.strip()[:5]) if value.strip() else None
    except ValueError:
        return None


def _short(text: object) -> str:
    return str(text).strip()[:MAX_TEXT]


def _clean_roadmap(data: Any) -> Roadmap | None:
    """The AI's roadmap, trimmed to the limits; an unusable one is dropped, not the plan."""
    try:
        weeks = tuple(
            Milestone(
                theme=_short(w["theme"]),
                goal=_short(w["goal"]),
                lessons=tuple(_short(x) for x in w["lessons"] if str(x).strip())[:7],
            )
            for w in data["weeks"][:MAX_WEEKS]
        )
        return Roadmap(outcome=_short(data["outcome"]), weeks=weeks)
    except (KeyError, TypeError, DomainError):
        logger.warning("AI roadmap was unusable; the plan goes without one")
        return None


def _clean_key(key: str, index: int) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]", "", key.lower())[:40]
    return cleaned or f"task{index}"


class LlmPlanGenerator:
    def __init__(self, pool: LlmPool, fallback: TemplatePlanGenerator) -> None:
        self._pool = pool
        self._fallback = fallback

    async def propose(self, answers: OnboardingAnswers) -> PlanProposal:
        try:
            return await self.ask(answers)
        except DomainError:
            raise
        except Exception:
            logger.exception("AI plan generation failed; using the template plan")
            return await self._fallback.propose(answers)

    async def ask(self, answers: OnboardingAnswers) -> PlanProposal:
        """The AI's plan without the template fallback (used by `pit.cli ai-check`)."""
        budgets = [answers.availability.budget(d) for d in range(7)]
        user_text = json.dumps(
            {
                "maqsad": answers.goal,
                "sabab": answers.motivation,
                "hozirgi_daraja": answers.current_level,
                "tosiqlar": answers.obstacles,
                "kunlik_budjet_daqiqa_dushanbadan": budgets,
            },
            ensure_ascii=False,
        )
        proposal, _ = await self._pool.complete(
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": PLAN_PROMPT.format(
                        language=PLAN_LANGUAGE.get(answers.language, PLAN_LANGUAGE["uz"])
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "plan", "strict": True, "schema": PLAN_SCHEMA},
            },
            parse=lambda raw: self._to_proposal(json.loads(raw), answers),
        )
        return proposal

    @staticmethod
    def _to_proposal(data: dict[str, Any], answers: OnboardingAnswers) -> PlanProposal:
        days = (list(data["week"]) + [[]] * 7)[:7]
        week = tuple(
            tuple(
                TaskSpec(
                    key=_clean_key(str(t["key"]), i),
                    title=str(t["title"])[:120] or "Vazifa",
                    minutes=max(5, min(int(t["minutes"]), 720)),
                    required=bool(t["required"]) or i == 0,
                    at=_clean_time(str(t.get("at", ""))),
                )
                for i, t in enumerate(tasks[:3])
            )
            for tasks in days
        )
        schedule = fit_to_availability(Schedule(week=week), answers)
        duration = int(data["duration_days"])
        return PlanProposal(
            title=str(data["title"])[:200],
            description=str(data["description"])[:1000],
            category=Category(data["category"]),
            duration_days=duration if duration in ALLOWED_DURATIONS else 30,
            difficulty=min(max(int(data["difficulty"]), 1), 5),
            verification_prompt=str(data["verification_prompt"])[:1000],
            schedule=schedule,
            roadmap=_clean_roadmap(data.get("roadmap")),
        )
