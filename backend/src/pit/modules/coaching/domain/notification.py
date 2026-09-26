from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pit.modules.coaching.domain.messages import Moment
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class NotificationCreated(DomainEvent):
    """Delivery channels (Telegram, push) subscribe to this."""

    notification_id: UUID
    user_id: UUID


@dataclass(eq=False, kw_only=True)
class Notification(AggregateRoot):
    user_id: UUID
    moment: Moment
    title: str
    body: str
    created_at: datetime
    participation_id: UUID | None = None
    read_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        notification_id: UUID,
        user_id: UUID,
        moment: Moment,
        title: str,
        body: str,
        created_at: datetime,
        participation_id: UUID | None = None,
    ) -> Notification:
        notification = cls(
            id=notification_id,
            user_id=user_id,
            moment=moment,
            title=title,
            body=body,
            created_at=created_at,
            participation_id=participation_id,
        )
        notification._record(NotificationCreated(notification_id=notification_id, user_id=user_id))
        return notification

    def mark_read(self, at: datetime) -> None:
        if self.read_at is None:
            self.read_at = at
