from datetime import date
from html import escape
from typing import Protocol

from pit.modules.challenges.domain.repositories import ChallengeRepository, ParticipationRepository
from pit.modules.coaching.domain.repositories import NotificationRepository
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.telegram.application.ports import Button, Keyboard
from pit.modules.telegram.application.texts import MONTHS, WEEKDAYS, pick
from pit.modules.verification.domain.repositories import ProofRepository
from pit.shared.application.unit_of_work import Transaction

TODAY_CALLBACK = "today"
CHEER_CALLBACK = "cheer"  # cheer:<notification hex> — applaud the friend the news is about


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


def human_date(day: date, locale: str = "uz") -> str:
    lang = pick(locale)
    weekday, month = WEEKDAYS[lang][day.weekday()], MONTHS[lang][day.month - 1]
    return f"{weekday}, {day.day} {month}" if lang == "ru" else f"{weekday}, {day.day}-{month}"


def site_row(web_url: str, path: str, text: str = "🌐 Saytda ochish") -> list[Button]:
    # Telegram rejects URL buttons that point to localhost, so they appear only in production.
    if not web_url.startswith("https://"):
        return []
    return [Button(text, url=f"{web_url.rstrip('/')}{path}")]


def keyboard(*rows: list[Button]) -> Keyboard:
    return [row for row in rows if row]
