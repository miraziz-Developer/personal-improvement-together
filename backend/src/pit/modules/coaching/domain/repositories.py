from typing import Protocol
from uuid import UUID

from pit.modules.coaching.domain.notification import Notification


class NotificationRepository(Protocol):
    def add(self, notification: Notification) -> None: ...

    async def get(self, notification_id: UUID) -> Notification | None: ...
