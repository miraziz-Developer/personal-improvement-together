from datetime import date
from html import escape
from typing import Protocol

from pit.modules.challenges.domain.repositories import ChallengeRepository, ParticipationRepository
from pit.modules.coaching.domain.repositories import NotificationRepository
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.telegram.application.ports import Button, Keyboard
from pit.modules.verification.domain.repositories import ProofRepository
from pit.shared.application.unit_of_work import Transaction

MONTHS = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)  # fmt: skip
WEEKDAYS = ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba")

TODAY_CALLBACK = "today"


class TelegramUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def challenges(self) -> ChallengeRepository: ...

    @property
    def participations(self) -> ParticipationRepository: ...

    @property
    def proofs(self) -> ProofRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...


def html(text: str) -> str:
    """Messages use Telegram's HTML mode; everything user-written must be escaped."""
    return escape(text, quote=False)


def human_date(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.day}-{MONTHS[day.month - 1]}"


def site_row(web_url: str, path: str, text: str = "🌐 Saytda ochish") -> list[Button]:
    # Telegram rejects URL buttons that point to localhost, so they appear only in production.
    if not web_url.startswith("https://"):
        return []
    return [Button(text, url=f"{web_url.rstrip('/')}{path}")]


def keyboard(*rows: list[Button]) -> Keyboard:
    return [row for row in rows if row]
