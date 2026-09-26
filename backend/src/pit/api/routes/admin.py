from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from pit.api import schemas as s
from pit.api.deps import ContainerDep, ModeratorId
from pit.jobs import close_all_days, send_nudges
from pit.modules.challenges.infrastructure.tables import challenges, participations
from pit.modules.identity.infrastructure.tables import users
from pit.modules.verification.application.commands import ReviewProof
from pit.modules.verification.domain.verdict import ProofStatus
from pit.modules.verification.infrastructure.tables import proofs

router = APIRouter(prefix="/admin", tags=["moderation"])


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
            .order_by(participations.c.stake.desc(), proofs.c.submitted_at)  # money first
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
