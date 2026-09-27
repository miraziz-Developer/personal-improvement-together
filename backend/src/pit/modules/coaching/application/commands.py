from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class SendDailyNudges(Command):
    """Scheduled: 08:00 "morning" plan of the day, 20:00 "evening" reminder if tasks remain."""

    kind: Literal["morning", "evening"]


@dataclass(frozen=True, kw_only=True)
class SendTaskReminders(Command):
    """Scheduled every few minutes: "it's time" for tasks the user gave a clock time."""


@dataclass(frozen=True, kw_only=True)
class MarkNotificationsRead(Command):
    user_id: UUID
    notification_ids: tuple[UUID, ...]


@dataclass(frozen=True, kw_only=True)
class SendWeeklySummaries(Command):
    """Scheduled: Sunday 21:00 — how the week went, per user."""


@dataclass(frozen=True, kw_only=True)
class CheerFriend(Command):
    """A group member applauds a friend; at most once a day per pair."""

    user_id: UUID
    participation_id: UUID  # the sender's own run, which ties them to the group
    friend_username: str
    emoji: str = "👏"
