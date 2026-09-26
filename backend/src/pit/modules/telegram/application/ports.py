"""What the Telegram bot needs from the outside world. Adapters live in infrastructure."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Button:
    """An inline button: either sends `callback` data back to the bot or opens `url`."""

    text: str
    callback: str | None = None
    url: str | None = None


type Keyboard = Sequence[Sequence[Button]]


@dataclass(frozen=True, slots=True)
class ShareContact:
    """A menu button that sends the user's own phone number, confirmed by Telegram."""

    text: str


# The persistent menu under the input field: rows of button labels; tapping one sends its text.
# An empty menu removes it.
type Menu = Sequence[Sequence[str | ShareContact]]


@dataclass(frozen=True, slots=True)
class Incoming:
    """One user action, already parsed from Telegram's update JSON."""

    chat_id: int
    text: str | None = None
    photo_file_id: str | None = None
    caption: str | None = None
    callback_id: str | None = None
    callback_data: str | None = None
    contact_phone: str | None = None
    contact_is_own: bool = False  # the sender's own number, not someone else's contact card


class ChatUnavailable(Exception):
    """The user blocked the bot or deleted the chat — stop writing to it."""


class TelegramUnavailable(Exception):
    """Network error or Telegram outage. Never fatal for the platform's own work."""


class TelegramApi(Protocol):
    async def send(
        self, chat_id: int, text: str, keyboard: Keyboard = (), *, menu: Menu | None = None
    ) -> None:
        """`keyboard` (buttons under the message) and `menu` cannot go in one message."""

    async def answer_callback(self, callback_id: str, text: str = "") -> None: ...

    async def download(self, file_id: str) -> bytes: ...


class ProofFiles(Protocol):
    """Cleans and stores a proof photo; returns (storage key, perceptual hash)."""

    async def save(self, user_id: UUID, data: bytes) -> tuple[str, str]: ...


class Conversation(Protocol):
    """Short-lived per-chat memory: which task the next proof is for, or a photo that arrived
    before the task was chosen. Forgotten after half an hour."""

    async def get(self, chat_id: int) -> dict[str, str]: ...

    async def update(self, chat_id: int, **values: str) -> None: ...

    async def clear(self, chat_id: int) -> None: ...
