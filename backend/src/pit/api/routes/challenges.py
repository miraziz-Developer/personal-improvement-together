import asyncio
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from pit.api import schemas as s
from pit.api import views
from pit.api.deps import ContainerDep, UserId
from pit.api.ratelimit import rate_limit
from pit.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from pit.modules.challenges.application.commands import (
    CancelParticipation,
    ChangeSchedule,
    JoinChallenge,
)
from pit.modules.challenges.domain.challenge import ApprovalStatus
from pit.modules.challenges.domain.participation import Participation
from pit.modules.challenges.infrastructure.tables import challenges, participations
from pit.modules.verification.application.commands import SubmitProof
from pit.modules.verification.infrastructure.images import MAX_UPLOAD_BYTES, prepare_proof_image
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied

router = APIRouter(tags=["challenges"])


async def _owned(uow: SqlAlchemyUnitOfWork, participation_id: UUID, user_id: UUID) -> Participation:
    participation = require(await uow.participations.get(participation_id), "Challenge topilmadi")
    if participation.user_id != user_id:
        raise PermissionDenied("Bu sizning challenge'ingiz emas")
    return participation


@router.get("/challenges", response_model=list[s.ChallengeOut])
async def catalog(container: ContainerDep) -> list[s.ChallengeOut]:
    async with container.uow_factory() as uow:
        ids = await uow.session.execute(
            select(challenges.c.id)
            .where(
                challenges.c.is_template.is_(True),
                challenges.c.approval_status == ApprovalStatus.APPROVED.value,
            )
            .order_by(challenges.c.difficulty, challenges.c.title)
        )
        counts = await views.participant_counts(uow)
        result = []
        for challenge_id in ids.scalars():
            challenge = require(await uow.challenges.get(challenge_id), "Challenge topilmadi")
            result.append(views.challenge_out(challenge, counts.get(challenge_id, 0)))
        return result


@router.get("/challenges/{challenge_id}", response_model=s.ChallengeOut)
async def challenge_detail(challenge_id: UUID, container: ContainerDep) -> s.ChallengeOut:
    async with container.uow_factory() as uow:
        challenge = require(await uow.challenges.get(challenge_id), "Challenge topilmadi")
        counts = await views.participant_counts(uow)
        return views.challenge_out(challenge, counts.get(challenge_id, 0))


@router.post("/challenges/{challenge_id}/join", response_model=s.IdOut, status_code=201)
async def join(
    challenge_id: UUID, body: s.JoinIn, user_id: UserId, container: ContainerDep
) -> s.IdOut:
    participation_id = await container.bus.handle(
        JoinChallenge(
            user_id=user_id,
            challenge_id=challenge_id,
            mode=body.mode,
            stake_amount=body.stake_amount,
            start_date=body.start_date,
            schedule=s.week_to_schedule(body.week) if body.week else None,
        )
    )
    return s.IdOut(id=participation_id)


@router.get("/me/participations", response_model=list[s.ParticipationOut])
async def my_participations(user_id: UserId, container: ContainerDep) -> list[s.ParticipationOut]:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        today = local_date(container.clock.now(), user.timezone)
        ids = await uow.session.execute(
            select(participations.c.id)
            .where(participations.c.user_id == user_id)
            .order_by(participations.c.created_at.desc())
        )
        result = []
        for participation_id in ids.scalars():
            p = require(await uow.participations.get(participation_id), "Challenge topilmadi")
            challenge = require(await uow.challenges.get(p.challenge_id), "Challenge topilmadi")
            result.append(views.participation_out(p, challenge, today))
        return result


@router.get("/me/participations/{participation_id}", response_model=s.ParticipationDetailOut)
async def participation_detail(
    participation_id: UUID, user_id: UserId, container: ContainerDep
) -> s.ParticipationDetailOut:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        p = await _owned(uow, participation_id, user_id)
        today = local_date(container.clock.now(), user.timezone)
        secret = container.settings.daily_code_secret.get_secret_value().encode()
        return await views.participation_detail(uow, p, today, secret)


@router.post("/me/participations/{participation_id}/cancel", status_code=204)
async def cancel(participation_id: UUID, user_id: UserId, container: ContainerDep) -> None:
    await container.bus.handle(
        CancelParticipation(user_id=user_id, participation_id=participation_id)
    )


@router.put("/me/participations/{participation_id}/schedule", status_code=204)
async def change_schedule(
    participation_id: UUID, body: s.ScheduleIn, user_id: UserId, container: ContainerDep
) -> None:
    await container.bus.handle(
        ChangeSchedule(
            user_id=user_id,
            participation_id=participation_id,
            schedule=s.week_to_schedule(body.week),
        )
    )


@router.post(
    "/proofs",
    response_model=s.ProofOut,
    status_code=201,
    tags=["proofs"],
    dependencies=[Depends(rate_limit("proofs", 40, 3600, per="user"))],
)
async def submit_proof(
    user_id: UserId,
    container: ContainerDep,
    participation_id: Annotated[UUID, Form()],
    task_key: Annotated[str, Form()] = "main",
    text_note: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> s.ProofOut:
    file_key = phash = None
    if file is not None and file.filename:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        image, phash = await asyncio.to_thread(prepare_proof_image, data)
        file_key = f"proofs/{user_id}/{uuid4()}.jpg"
        await container.storage.put(file_key, image, "image/jpeg")
    proof_id = await container.bus.handle(
        SubmitProof(
            user_id=user_id,
            participation_id=participation_id,
            task_key=task_key,
            file_key=file_key,
            text_note=text_note,
            phash=phash,
        )
    )
    return await proof_status(proof_id, user_id, container)


@router.get("/proofs/{proof_id}", response_model=s.ProofOut, tags=["proofs"])
async def proof_status(proof_id: UUID, user_id: UserId, container: ContainerDep) -> s.ProofOut:
    async with container.uow_factory() as uow:
        proof = require(await uow.proofs.get(proof_id), "Isbot topilmadi")
        if proof.user_id != user_id:
            raise PermissionDenied("Bu sizning isbotingiz emas")
        reason = (
            proof.review.note
            if proof.review
            else proof.ai_verdict.reason
            if proof.ai_verdict
            else None
        )
        return s.ProofOut(
            id=proof.id,
            status=proof.status.value,
            task_key=proof.task_key,
            for_date=proof.for_date,
            reason=reason or None,
            reviewed_by_human=proof.review is not None,
        )
