from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class SendDailyNudges(Command):
    """Scheduled: 08:00 "morning" plan of the day, 20:00 "evening" reminder if tasks remain."""

    kind: Literal["morning", "evening"]


@dataclass(frozen=True, kw_only=True)
class MarkNotificationsRead(Command):
    user_id: UUID
    notification_ids: tuple[UUID, ...]
