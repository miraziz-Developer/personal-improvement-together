from dataclasses import dataclass
from uuid import UUID

from pit.modules.moderation.domain.report import ReportAction, ReportReason
from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class FileReport(Command):
    reporter_id: UUID
    reported_username: str
    reason: ReportReason
    details: str = ""


@dataclass(frozen=True, kw_only=True)
class ResolveReport(Command):
    report_id: UUID
    moderator_id: UUID
    action: ReportAction
