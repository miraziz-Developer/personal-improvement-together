from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import delete

from pit.modules.push.domain.subscription import PushSubscription
from pit.modules.push.infrastructure.tables import push_subscriptions
from pit.shared.infrastructure.repository import Row, SqlRepository


class SqlPushSubscriptionRepository(SqlRepository[PushSubscription]):
    table = push_subscriptions

    def _to_row(self, item: PushSubscription) -> Row:
        return {
            "id": item.id,
            "user_id": item.user_id,
            "endpoint": item.endpoint,
            "p256dh": item.p256dh,
            "auth": item.auth,
            "created_at": item.created_at,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> PushSubscription:
        return PushSubscription(
            id=row["id"],
            user_id=row["user_id"],
            endpoint=row["endpoint"],
            p256dh=row["p256dh"],
            auth=row["auth"],
            created_at=row["created_at"],
        )

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        pending = self._pending(lambda s: s.endpoint == endpoint)
        if pending:
            return pending[0]
        found = await self._select(push_subscriptions.c.endpoint == endpoint)
        return found[0] if found else None

    async def list_for_user(self, user_id: UUID) -> list[PushSubscription]:
        stored = await self._select(push_subscriptions.c.user_id == user_id)
        return stored + self._pending(lambda s: s.user_id == user_id)

    async def remove(self, subscription: PushSubscription) -> None:
        self._new.pop(subscription.id, None)
        self._loaded.pop(subscription.id, None)
        await self._session.execute(
            delete(push_subscriptions).where(push_subscriptions.c.id == subscription.id)
        )
