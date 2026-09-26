"""A user reports another user; a moderator decides."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvalidStateTransition

MAX_DETAILS = 500


class ReportReason(StrEnum):
    ABUSE = "abuse"  # insults, bullying
    BAD_NAME = "bad_name"  # offensive username
    SPAM = "spam"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class ReportAction(StrEnum):
    DISMISS = "dismiss"
    RESET_USERNAME = "reset_username"


@dataclass(eq=False, kw_only=True)
class Report(AggregateRoot):
    reporter_id: UUID
    reported_user_id: UUID
    reason: ReportReason
    details: str
    created_at: datetime
    status: ReportStatus = ReportStatus.OPEN
    resolved_by: UUID | None = None
    resolved_at: datetime | None = None

    @classmethod
    def file(
        cls,
        *,
        report_id: UUID,
        reporter_id: UUID,
        reported_user_id: UUID,
        reason: ReportReason,
        details: str,
        at: datetime,
    ) -> Report:
        if reporter_id == reported_user_id:
            raise DomainError("O'zingiz haqingizda shikoyat qilib bo'lmaydi")
        return cls(
            id=report_id,
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            reason=reason,
            details=details.strip()[:MAX_DETAILS],
            created_at=at,
        )

    def resolve(self, *, moderator_id: UUID, action: ReportAction, at: datetime) -> None:
        if self.status is not ReportStatus.OPEN:
            raise InvalidStateTransition("Bu shikoyat allaqachon ko'rib chiqilgan")
        self.status = (
            ReportStatus.DISMISSED if action is ReportAction.DISMISS else ReportStatus.ACTIONED
        )
        self.resolved_by = moderator_id
        self.resolved_at = at


class ReportRepository(Protocol):
    def add(self, report: Report) -> None: ...

    async def get(self, report_id: UUID) -> Report | None: ...

    async def has_open(self, reporter_id: UUID, reported_user_id: UUID) -> bool: ...
