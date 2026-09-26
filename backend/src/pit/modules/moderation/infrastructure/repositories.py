from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pit.modules.moderation.domain.report import Report, ReportReason, ReportStatus
from pit.modules.moderation.infrastructure.tables import reports
from pit.shared.infrastructure.repository import Row, SqlRepository


class SqlReportRepository(SqlRepository[Report]):
    table = reports

    def _to_row(self, item: Report) -> Row:
        return {
            "id": item.id,
            "reporter_id": item.reporter_id,
            "reported_user_id": item.reported_user_id,
            "reason": item.reason.value,
            "details": item.details,
            "status": item.status.value,
            "resolved_by": item.resolved_by,
            "resolved_at": item.resolved_at,
            "created_at": item.created_at,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Report:
        return Report(
            id=row["id"],
            reporter_id=row["reporter_id"],
            reported_user_id=row["reported_user_id"],
            reason=ReportReason(row["reason"]),
            details=row["details"],
            created_at=row["created_at"],
            status=ReportStatus(row["status"]),
            resolved_by=row["resolved_by"],
            resolved_at=row["resolved_at"],
        )

    async def has_open(self, reporter_id: UUID, reported_user_id: UUID) -> bool:
        if self._pending(
            lambda r: r.reporter_id == reporter_id and r.reported_user_id == reported_user_id
        ):
            return True
        return await self._exists(
            reports.c.reporter_id == reporter_id,
            reports.c.reported_user_id == reported_user_id,
            reports.c.status == ReportStatus.OPEN.value,
        )
