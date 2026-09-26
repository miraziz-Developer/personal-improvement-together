"""Reports: a user flags another, a moderator decides."""

import pytest

from pit.modules.identity.domain.user import Role
from pit.modules.moderation.application.commands import FileReport, ResolveReport
from pit.modules.moderation.domain.report import ReportAction, ReportReason, ReportStatus
from pit.shared.domain.errors import DomainError, InvalidStateTransition
from tests.application.conftest import World


async def test_a_moderator_can_clean_an_offensive_username(world: World) -> None:
    reporter, rude, moderator = (
        world.add_user(),
        world.add_user(),
        world.add_user(role=Role.MODERATOR),
    )
    report_id = await world.bus.handle(
        FileReport(
            reporter_id=reporter.id, reported_username=rude.username, reason=ReportReason.BAD_NAME
        )
    )
    with pytest.raises(DomainError, match="ko'rib chiqilmoqda"):  # one open report per pair
        await world.bus.handle(
            FileReport(
                reporter_id=reporter.id, reported_username=rude.username, reason=ReportReason.SPAM
            )
        )

    await world.bus.handle(
        ResolveReport(
            report_id=report_id, moderator_id=moderator.id, action=ReportAction.RESET_USERNAME
        )
    )
    assert rude.username.startswith("user_")
    assert world.store.reports[report_id].status is ReportStatus.ACTIONED
    with pytest.raises(InvalidStateTransition):
        await world.bus.handle(
            ResolveReport(
                report_id=report_id, moderator_id=moderator.id, action=ReportAction.DISMISS
            )
        )


async def test_you_cannot_report_yourself_or_a_stranger(world: World) -> None:
    user = world.add_user()
    with pytest.raises(DomainError, match="O'zingiz"):
        await world.bus.handle(
            FileReport(
                reporter_id=user.id, reported_username=user.username, reason=ReportReason.OTHER
            )
        )
    with pytest.raises(DomainError, match="topilmadi"):
        await world.bus.handle(
            FileReport(reporter_id=user.id, reported_username="yoq_odam", reason=ReportReason.OTHER)
        )


async def test_a_dismissed_report_lets_the_user_report_again(world: World) -> None:
    reporter, other, moderator = (
        world.add_user(),
        world.add_user(),
        world.add_user(role=Role.MODERATOR),
    )
    first = await world.bus.handle(
        FileReport(
            reporter_id=reporter.id, reported_username=other.username, reason=ReportReason.SPAM
        )
    )
    await world.bus.handle(
        ResolveReport(report_id=first, moderator_id=moderator.id, action=ReportAction.DISMISS)
    )
    assert await world.bus.handle(
        FileReport(
            reporter_id=reporter.id, reported_username=other.username, reason=ReportReason.SPAM
        )
    )
