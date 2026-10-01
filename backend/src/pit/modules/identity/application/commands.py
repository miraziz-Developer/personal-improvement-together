from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from pit.modules.identity.domain.user import DEFAULT_TIMEZONE
from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class RegisterUser(Command):
    username: str
    password: str = field(repr=False)
    birth_date: date
    region_id: UUID
    # Version of the Terms/Privacy the user ticked on the form; empty = not accepted.
    accepted_terms_version: str = ""
    timezone: str = DEFAULT_TIMEZONE


@dataclass(frozen=True, kw_only=True)
class RequestPhoneCode(Command):
    user_id: UUID
    phone: str


@dataclass(frozen=True, kw_only=True)
class RequestPasswordReset(Command):
    username: str


@dataclass(frozen=True, kw_only=True)
class ResetPassword(Command):
    username: str
    code: str = field(repr=False)
    new_password: str = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class ConfirmPhone(Command):
    user_id: UUID
    code: str = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class IssueTelegramLink(Command):
    """Returns a one-time token for t.me/<bot>?start=<token>."""

    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class LinkTelegram(Command):
    """The bot received /start <token> from this chat. Returns the linked user's id."""

    token: str = field(repr=False)
    chat_id: int


@dataclass(frozen=True, kw_only=True)
class UnlinkTelegram(Command):
    """From the website (user_id) or from the bot's /stop or a blocked chat (chat_id)."""

    user_id: UUID | None = None
    chat_id: int | None = None


@dataclass(frozen=True, kw_only=True)
class VerifyPhoneFromTelegram(Command):
    """The user shared their own contact with the bot: Telegram vouches for the number."""

    chat_id: int
    phone: str


@dataclass(frozen=True, kw_only=True)
class SignInWithGoogle(Command):
    """Returns the user's id, or the GoogleIdentity when no account uses it yet."""

    credential: str = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class RegisterWithGoogle(Command):
    google_sub: str
    email: str | None
    username: str
    birth_date: date
    region_id: UUID
    accepted_terms_version: str = ""
    timezone: str = DEFAULT_TIMEZONE


@dataclass(frozen=True, kw_only=True)
class RegisterWithTelegram(Command):
    """A new account from inside the Telegram app; its chat is linked from the start."""

    chat_id: int
    username: str
    birth_date: date
    region_id: UUID
    accepted_terms_version: str = ""
    timezone: str = DEFAULT_TIMEZONE


@dataclass(frozen=True, kw_only=True)
class LinkTelegramChat(Command):
    """A signed-in user opened the site inside Telegram: Telegram vouched for the chat."""

    user_id: UUID
    chat_id: int


@dataclass(frozen=True, kw_only=True)
class EraseAccount(Command):
    """Typing the username again guards against a stray click."""

    user_id: UUID
    confirm_username: str


@dataclass(frozen=True, kw_only=True)
class ChangeLocale(Command):
    user_id: UUID
    locale: str
