from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

from pit.modules.identity.domain.events import AccountErased, PhoneVerified, UserRegistered
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvariantViolation

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
UZ_PHONE_RE = re.compile(r"^\+998\d{9}$")
DEFAULT_TIMEZONE = "Asia/Tashkent"
MIN_AGE = 7
MIN_PASSWORD_LENGTH = 8
# Bump when the Terms / Privacy Policy change; users then accept the new version.
CURRENT_TERMS_VERSION = "2026-09-25"


class Locale(StrEnum):
    """The language the platform speaks to the user (coach, bot, e-mails)."""

    UZ = "uz"
    RU = "ru"


class Role(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


REMIND_BEFORE_CHOICES = (0, 5, 10, 15, 30)  # minutes before a timed task; 0 = no heads-up


@dataclass(frozen=True, slots=True)
class NotificationPrefs:
    """How the coach may reach the user. Quiet hours hold back Telegram and push messages
    (they still appear in the app); friends' news can be turned off."""

    remind_before: int = 10
    quiet_from: time | None = None
    quiet_to: time | None = None
    friends_news: bool = True

    def __post_init__(self) -> None:
        if self.remind_before not in REMIND_BEFORE_CHOICES:
            raise InvariantViolation("Eslatma vaqti 0, 5, 10, 15 yoki 30 daqiqa bo'lsin")
        if (self.quiet_from is None) != (self.quiet_to is None):
            raise InvariantViolation("Tinch soatlarning boshi va oxirini birga belgilang")
        if self.quiet_from is not None and self.quiet_from == self.quiet_to:
            raise InvariantViolation("Tinch soatlarning boshi va oxiri har xil bo'lsin")

    def is_quiet(self, at: time) -> bool:
        if self.quiet_from is None or self.quiet_to is None:
            return False
        if self.quiet_from < self.quiet_to:
            return self.quiet_from <= at < self.quiet_to
        return at >= self.quiet_from or at < self.quiet_to  # across midnight, e.g. 23:00-07:00


@dataclass(eq=False, kw_only=True)
class User(AggregateRoot):
    username: str
    # Full date: the 7+ rule is exact; leaderboards use only birth_year.
    birth_date: date
    region_id: UUID
    timezone: str = DEFAULT_TIMEZONE
    phone: str | None = None
    phone_verified: bool = False
    role: Role = Role.USER
    password_hash: str = ""  # empty = cannot log in with a password
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None
    # Telegram chat the coach writes to; None = not linked (or the user blocked the bot).
    telegram_chat_id: int | None = None
    # "Sign in with Google": the account's stable Google id; such users may have no password.
    google_sub: str | None = None
    email: str | None = None
    deleted_at: datetime | None = None  # erased at the user's request; only statistics remain
    locale: Locale = Locale.UZ
    notifications: NotificationPrefs = field(default_factory=NotificationPrefs)

    @classmethod
    def register(
        cls,
        *,
        user_id: UUID,
        username: str,
        birth_date: date,
        region_id: UUID,
        today: date,
        timezone: str = DEFAULT_TIMEZONE,
        password_hash: str = "",
    ) -> User:
        username = username.strip().lower()
        if not USERNAME_RE.fullmatch(username):
            raise InvariantViolation(
                "Username 3-30 belgi: kichik lotin harflari, raqamlar va '_' bo'lishi kerak"
            )
        if not MIN_AGE <= age_on(birth_date, today) <= 100:
            raise InvariantViolation(f"Platformadan {MIN_AGE} yoshdan foydalanish mumkin")
        user = cls(
            id=user_id,
            username=username,
            birth_date=birth_date,
            region_id=region_id,
            timezone=timezone,
            password_hash=password_hash,
        )
        user._record(
            UserRegistered(user_id=user_id, birth_year=birth_date.year, region_id=region_id)
        )
        return user

    @property
    def birth_year(self) -> int:
        """Cohort key for the peer leaderboard."""
        return self.birth_date.year

    @property
    def is_moderator(self) -> bool:
        return self.role in (Role.MODERATOR, Role.ADMIN)

    def verify_phone(self, phone: str) -> None:
        self.phone = normalize_phone(phone)
        self.phone_verified = True
        self._record(PhoneVerified(user_id=self.id))

    def accept_terms(self, version: str, at: datetime) -> None:
        if version != CURRENT_TERMS_VERSION:
            raise DomainError("Foydalanish shartlari yangilangan. Iltimos, sahifani yangilang")
        self.terms_version = version
        self.terms_accepted_at = at

    def link_telegram(self, chat_id: int) -> None:
        self.telegram_chat_id = chat_id

    def unlink_telegram(self) -> None:
        self.telegram_chat_id = None

    @property
    def is_erased(self) -> bool:
        return self.deleted_at is not None

    def erase(self, at: datetime) -> None:
        """The right to be forgotten: identifying data goes, the anonymous record of days stays
        (group and ranking history keep adding up). Birth date keeps only the cohort year."""
        if self.is_erased:
            raise DomainError("Akkaunt allaqachon o'chirilgan")
        self.username = f"deleted_{self.id.hex[:10]}"
        self.birth_date = date(self.birth_date.year, 1, 1)
        self.phone = None
        self.phone_verified = False
        self.password_hash = ""
        self.telegram_chat_id = None
        self.google_sub = None
        self.email = None
        self.deleted_at = at
        self._record(AccountErased(user_id=self.id))

    def change_locale(self, locale: Locale) -> None:
        self.locale = locale

    def change_notifications(self, prefs: NotificationPrefs) -> None:
        self.notifications = prefs

    def is_quiet_now(self, now: datetime) -> bool:
        """Inside the user's quiet hours, in their own time zone."""
        return self.notifications.is_quiet(now.astimezone(ZoneInfo(self.timezone)).time())

    def reset_username(self) -> None:
        """A moderator removes an offensive username; the user may pick a new one later."""
        self.username = f"user_{self.id.hex[:10]}"

    def connect_google(self, sub: str, email: str | None) -> None:
        self.google_sub = sub
        self.email = email

    def change_password(self, password_hash: str) -> None:
        self.password_hash = password_hash

    def promote_to_moderator(self) -> None:
        self.role = Role.MODERATOR

    def ensure_can_stake(self) -> None:
        # Any age may stake (for children the parent pays); a verified phone limits multi-accounts.
        if not self.phone_verified:
            raise DomainError("Pul qo'yish uchun avval telefon raqamingizni tasdiqlang")


def ensure_strong_password(password: str) -> None:
    """Checked before hashing — the domain never sees the plain password again."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvariantViolation(f"Parol kamida {MIN_PASSWORD_LENGTH} belgi bo'lsin")
    if password.isdigit() or password.isalpha():
        raise InvariantViolation("Parolda harf ham, raqam ham bo'lsin")


def normalize_phone(phone: str) -> str:
    phone = phone.replace(" ", "").replace("-", "")
    if phone.isdigit():
        phone = f"+{phone}"  # Telegram shares contacts without the "+"
    if not UZ_PHONE_RE.fullmatch(phone):
        raise InvariantViolation("Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak")
    return phone
