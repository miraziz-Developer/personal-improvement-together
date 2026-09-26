"""The user's rights over their data: take a copy, or erase the account."""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select

from pit.api import schemas as s
from pit.api import views
from pit.api.deps import ContainerDep, UserId, revoked_key
from pit.api.ratelimit import rate_limit
from pit.modules.challenges.infrastructure.tables import participations
from pit.modules.coaching.infrastructure.tables import notifications
from pit.modules.identity.application.commands import EraseAccount
from pit.shared.application.lookup import require
from pit.shared.domain.errors import DomainError

router = APIRouter(tags=["privacy"])


@router.get("/me/export", dependencies=[Depends(rate_limit("export", 10, 3600, per="user"))])
async def export(user_id: UserId, container: ContainerDep) -> JSONResponse:
    """Everything the platform keeps about the user, as one JSON file."""
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        points, *_ = await views.user_stats(uow, user_id)
        runs: list[dict[str, Any]] = []
        ids = await uow.session.execute(
            select(participations.c.id)
            .where(participations.c.user_id == user_id)
            .order_by(participations.c.created_at)
        )
        for participation_id in ids.scalars():
            p = require(await uow.participations.get(participation_id), "Challenge topilmadi")
            challenge = await uow.challenges.get(p.challenge_id)
            runs.append(
                {
                    "challenge": challenge.title if challenge else None,
                    "status": p.status.value,
                    "mode": p.mode.value,
                    "start_date": p.start_date.isoformat(),
                    "end_date": p.end_date.isoformat(),
                    "days_completed": p.days_completed,
                    "current_streak": p.current_streak,
                    "best_streak": p.best_streak,
                    "in_group": p.group_id is not None,
                    "calendar": {d.isoformat(): st.value for d, st in sorted(p.days.items())},
                    "plan": [
                        [task.model_dump() for task in day]
                        for day in s.schedule_to_week(p.current_schedule)
                    ],
                }
            )
        proofs = []
        for proof in sorted(await uow.proofs.list_for_user(user_id), key=lambda x: x.submitted_at):
            proofs.append(
                {
                    "date": proof.for_date.isoformat(),
                    "task": proof.task_key,
                    "status": proof.status.value,
                    "note": proof.text_note,
                    "reason": proof.ai_verdict.reason if proof.ai_verdict else None,
                    "submitted_at": proof.submitted_at.isoformat(),
                    # A private link valid for 15 minutes: download the photos right away.
                    "photo_url": (
                        await container.storage.url(proof.file_key) if proof.file_key else None
                    ),
                }
            )
        rows = await uow.session.execute(
            select(notifications)
            .where(notifications.c.user_id == user_id)
            .order_by(notifications.c.created_at)
        )
        messages = [
            {
                "at": row["created_at"].isoformat(),
                "title": row["title"],
                "text": row["body"],
                "read": row["read_at"] is not None,
            }
            for row in rows.mappings()
        ]
        body = {
            "exported_at": container.clock.now().isoformat(),
            "profile": {
                "username": user.username,
                "birth_date": user.birth_date.isoformat(),
                "region": await views.region_name(uow, user.region_id),
                "timezone": user.timezone,
                "phone": user.phone,
                "phone_verified": user.phone_verified,
                "email": user.email,
                "google_linked": user.google_sub is not None,
                "telegram_linked": user.telegram_chat_id is not None,
                "terms_version": user.terms_version,
                "terms_accepted_at": (
                    user.terms_accepted_at.isoformat() if user.terms_accepted_at else None
                ),
            },
            "points": points,
            "challenges": runs,
            "proofs": proofs,
            "notifications": messages,
        }
    return JSONResponse(
        body,
        headers={"Content-Disposition": f'attachment; filename="pit-{user.username}.json"'},
    )


@router.delete(
    "/me",
    status_code=204,
    dependencies=[Depends(rate_limit("erase", 5, 3600, per="user"))],
)
async def erase(body: s.EraseIn, user_id: UserId, container: ContainerDep) -> None:
    async with container.uow_factory() as uow:
        if await uow.participations.count_open_stakes(user_id):
            raise DomainError(
                "Garovli challenge'ingiz tugamagan. U yakunlangach akkauntni o'chira olasiz"
            )
    await container.bus.handle(EraseAccount(user_id=user_id, confirm_username=body.username))
    # Tokens already issued stay valid until they expire; this makes them useless right away.
    ttl = container.settings.jwt_ttl_hours * 3600
    await container.redis.set(revoked_key(user_id), "1", ex=ttl)
