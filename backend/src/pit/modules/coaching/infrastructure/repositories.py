from collections.abc import Mapping
from typing import Any

from pit.modules.coaching.domain.messages import Moment
from pit.modules.coaching.domain.notification import Notification
from pit.modules.coaching.infrastructure.tables import notifications
from pit.shared.infrastructure.repository import Row, SqlRepository, utc


class SqlNotificationRepository(SqlRepository[Notification]):
    table = notifications

    def _to_row(self, item: Notification) -> Row:
        return {
            "id": item.id,
            "user_id": item.user_id,
            "moment": item.moment.value,
            "title": item.title,
            "body": item.body,
            "participation_id": item.participation_id,
            "sent_at": utc(item.created_at),
            "read_at": utc(item.read_at) if item.read_at else None,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Notification:
        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            moment=Moment(row["moment"]),
            title=row["title"],
            body=row["body"],
            created_at=row["sent_at"],
            participation_id=row["participation_id"],
            read_at=row["read_at"],
        )
