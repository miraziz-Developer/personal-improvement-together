from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.moderation.application.commands import FileReport, ResolveReport
from pit.modules.moderation.domain.report import Report, ReportAction, ReportRepository
from pit.shared.application.clock import Clock
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.errors import DomainError


class ModerationUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def reports(self) -> ReportRepository: ...


async def file_report(cmd: FileReport, uow: ModerationUoW, *, clock: Clock) -> UUID:
    async with uow:
        reported = require(
            await uow.users.get_by_username(cmd.reported_username.strip().lower()),
            "Foydalanuvchi topilmadi",
        )
        if await uow.reports.has_open(cmd.reporter_id, reported.id):
            raise DomainError("Shikoyatingiz qabul qilingan va ko'rib chiqilmoqda")
        report = Report.file(
            report_id=uuid4(),
            reporter_id=cmd.reporter_id,
            reported_user_id=reported.id,
            reason=cmd.reason,
            details=cmd.details,
            at=clock.now(),
        )
        uow.reports.add(report)
        await uow.commit()
        return report.id


async def resolve_report(cmd: ResolveReport, uow: ModerationUoW, *, clock: Clock) -> None:
    async with uow:
        report = require(await uow.reports.get(cmd.report_id), "Shikoyat topilmadi")
        report.resolve(moderator_id=cmd.moderator_id, action=cmd.action, at=clock.now())
        if cmd.action is ReportAction.RESET_USERNAME:
            user = require(await uow.users.get(report.reported_user_id), "Foydalanuvchi topilmadi")
            user.reset_username()
        await uow.commit()
