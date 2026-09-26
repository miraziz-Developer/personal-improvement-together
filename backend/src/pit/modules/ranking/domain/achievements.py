"""Badges: milestones earned from what the user has done. Derived, never stored — a rule
change applies to everyone at once, and nothing can drift out of sync."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Record:
    """What the badges are judged on."""

    days_done: int  # all participations together
    best_streak: int
    completed_challenges: int
    points: int
    in_group: bool
    telegram_linked: bool


@dataclass(frozen=True, slots=True)
class Badge:
    key: str
    emoji: str
    title: str
    hint: str  # how to earn it, shown while it is still locked
    earned: Callable[[Record], bool]


BADGES: tuple[Badge, ...] = (
    Badge(
        "first_day", "🌱", "Birinchi qadam", "Birinchi kunni bajaring", lambda r: r.days_done >= 1
    ),
    Badge("streak_7", "🔥", "Bir hafta olovda", "7 kunlik streak", lambda r: r.best_streak >= 7),
    Badge("streak_30", "⚡", "Temir iroda", "30 kunlik streak", lambda r: r.best_streak >= 30),
    Badge("streak_100", "💎", "Afsona", "100 kunlik streak", lambda r: r.best_streak >= 100),
    Badge("days_50", "🏃", "50 kun harakat", "Jami 50 kun bajaring", lambda r: r.days_done >= 50),
    Badge(
        "finisher",
        "🏆",
        "Marraga yetdi",
        "Challenge'ni oxirigacha yakunlang",
        lambda r: r.completed_challenges >= 1,
    ),
    Badge(
        "triple",
        "👑",
        "Uch karra g'olib",
        "3 ta challenge'ni yakunlang",
        lambda r: r.completed_challenges >= 3,
    ),
    Badge("points_1000", "⭐", "Ming ball", "1000 ball to'plang", lambda r: r.points >= 1000),
    Badge(
        "together",
        "🤝",
        "Birga kuchliroq",
        "Do'stlar bilan guruhga qo'shiling",
        lambda r: r.in_group,
    ),
    Badge(
        "connected",
        "📲",
        "Doim aloqada",
        "Telegram botni ulang",
        lambda r: r.telegram_linked,
    ),
)


def badges_for(record: Record) -> list[tuple[Badge, bool]]:
    return [(badge, badge.earned(record)) for badge in BADGES]
