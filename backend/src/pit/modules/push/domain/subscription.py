"""A browser that agreed to receive notifications for one user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import InvariantViolation

MAX_ENDPOINT = 1000


@dataclass(eq=False, kw_only=True)
class PushSubscription(AggregateRoot):
    user_id: UUID
    endpoint: str  # the browser vendor's push URL; unique per browser profile
    p256dh: str  # encryption keys issued by the browser
    auth: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.endpoint.startswith("https://") or len(self.endpoint) > MAX_ENDPOINT:
            raise InvariantViolation("Push obunasi noto'g'ri")
        if not self.p256dh or not self.auth:
            raise InvariantViolation("Push obunasi kalitlari yo'q")

    def move_to(self, user_id: UUID, *, p256dh: str, auth: str) -> None:
        """Someone else signed in on the same browser: the notifications follow them."""
        self.user_id, self.p256dh, self.auth = user_id, p256dh, auth


class PushSubscriptionRepository(Protocol):
    def add(self, subscription: PushSubscription) -> None: ...

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None: ...

    async def list_for_user(self, user_id: UUID) -> list[PushSubscription]: ...

    async def remove(self, subscription: PushSubscription) -> None: ...
