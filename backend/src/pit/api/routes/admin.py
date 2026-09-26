from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from pit.api import schemas as s
from pit.api.deps import ContainerDep, ModeratorId
from pit.jobs import close_all_days, send_nudges
from pit.modules.challenges.infrastructure.tables import challenges, participations
from pit.modules.identity.infrastructure.tables import users
from pit.modules.moderation.application.commands import ResolveReport
from pit.modules.moderation.domain.report import ReportAction, ReportStatus
from pit.modules.moderation.infrastructure.tables import reports
from pit.modules.verification.application.commands import ReviewProof
from pit.modules.verification.domain.verdict import ProofStatus
from pit.modules.verification.infrastructure.tables import proofs

router = APIRouter(prefix="/admin", tags=["moderation"])
reports_outer = reports.alias("r")


@router.get("/proofs", response_model=list[s.ReviewItemOut])
async def review_queue(moderator_id: ModeratorId, container: ContainerDep) -> list[s.ReviewItemOut]:
    async with container.uow_factory() as uow:
        rows = await uow.session.execute(
            select(
                proofs,
                users.c.username,
                challenges.c.title.label("challenge_title"),
                participations.c.stake,
            )
            .join(users, users.c.id == proofs.c.user_id)
            .join(participations, participations.c.id == proofs.c.participation_id)
            .join(challenges, challenges.c.id == participations.c.challenge_id)
            .where(proofs.c.status == ProofStatus.NEEDS_REVIEW.value)
            # Harmful content first, then money, then the oldest.
            .order_by(
                proofs.c.ai_unsafe.desc(), participations.c.stake.desc(), proofs.c.submitted_at
            )
            .limit(50)
        )
        items = []
        for row in rows.mappings():
            image_url = await container.storage.url(row["file_key"]) if row["file_key"] else None
            items.append(
                s.ReviewItemOut(
                    proof_id=row["id"],
                    username=row["username"],
                    challenge_title=row["challenge_title"],
                    task_key=row["task_key"],
                    for_date=row["for_date"],
                    text_note=row["text_note"],
                    image_url=image_url,
                    ai_reason=row["ai_reason"],
                    ai_confidence=row["ai_confidence"],
                    stake=row["stake"],
                    flagged=row["ai_unsafe"],
                )
            )
        return items


@router.post("/proofs/{proof_id}/review", status_code=204)
async def review(
    proof_id: UUID, body: s.ReviewIn, moderator_id: ModeratorId, container: ContainerDep
) -> None:
    await container.bus.handle(
        ReviewProof(
            proof_id=proof_id, reviewer_id=moderator_id, approved=body.approved, note=body.note
        )
    )


@router.post("/jobs/close-days")
async def run_close_days(moderator_id: ModeratorId, container: ContainerDep) -> dict[str, int]:
    return {"closed": await close_all_days(container)}


@router.post("/jobs/nudges/{kind}")
async def run_nudges(
    kind: Literal["morning", "evening"], moderator_id: ModeratorId, container: ContainerDep
) -> dict[str, int]:
    return {"sent": await send_nudges(container, kind)}


@router.get("/reports", response_model=list[s.ReportOut])
async def open_reports(moderator_id: ModeratorId, container: ContainerDep) -> list[s.ReportOut]:
    reporter, reported = users.alias("reporter"), users.alias("reported")
    against = (
        select(func.count())
        .where(
            reports.c.reported_user_id == reports_outer.c.reported_user_id,
            reports.c.status == ReportStatus.OPEN.value,
        )
        .scalar_subquery()
    )
    async with container.uow_factory() as uow:
        rows = await uow.session.execute(
            select(
                reports_outer,
                reporter.c.username.label("reporter"),
                reported.c.username.label("reported"),
                against.label("reports_against"),
            )
            .join(reporter, reporter.c.id == reports_outer.c.reporter_id)
            .join(reported, reported.c.id == reports_outer.c.reported_user_id)
            .where(reports_outer.c.status == ReportStatus.OPEN.value)
            .order_by(against.desc(), reports_outer.c.created_at)
            .limit(100)
        )
        return [
            s.ReportOut(
                id=row["id"],
                reporter=row["reporter"],
                reported=row["reported"],
                reason=row["reason"],
                details=row["details"],
                created_at=row["created_at"],
                reports_against=row["reports_against"],
            )
            for row in rows.mappings()
        ]


@router.post("/reports/{report_id}/resolve", status_code=204)
async def resolve_report(
    report_id: UUID, body: s.ResolveReportIn, moderator_id: ModeratorId, container: ContainerDep
) -> None:
    await container.bus.handle(
        ResolveReport(
            report_id=report_id, moderator_id=moderator_id, action=ReportAction(body.action)
        )
    )
