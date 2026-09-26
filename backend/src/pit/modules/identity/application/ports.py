from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pit.modules.identity.domain.user import User


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class OtpStore(Protocol):
    """Short-lived phone codes keyed by purpose ("phone:<user>", "reset:<user>").

    `verify` counts attempts and forgets the code after success or too many wrong tries,
    so a 6-digit code cannot be brute-forced."""

    async def put(self, key: str, phone: str, code: str) -> None: ...

    async def verify(self, key: str, code: str) -> str | None: ...


class LinkTokens(Protocol):
    """One-time tokens for deep links such as t.me/<bot>?start=<token>; they expire quickly."""

    async def issue(self, user_id: UUID) -> str: ...

    async def consume(self, token: str) -> UUID | None: ...


class PrivateMessenger(Protocol):
    """A free, private channel to the user (the Telegram bot). Returns False when the user
    cannot be reached there, so the caller can fall back to SMS."""

    async def send(self, user: User, text: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    sub: str
    email: str | None
    name: str | None = None


class GoogleVerifier(Protocol):
    """Checks a Google Sign-In ID token (signature, audience, expiry); DomainError if invalid."""

    async def verify(self, credential: str) -> GoogleIdentity: ...


class SmsSender(Protocol):
    async def send(self, phone: str, text: str) -> None: ...
