"""Together: invite friends to a challenge, see how the group is doing."""

from datetime import datetime
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from pit.api import schemas as s
from pit.api import views
from pit.api.deps import ContainerDep, LocaleDep, UserId
from pit.api.ratelimit import rate_limit
from pit.api.security import issue_share_token, read_share_token
from pit.catalog_ru import catalog_text
from pit.modules.challenges.application.commands import CreateGroup, JoinGroup, PostGroupMessage
from pit.modules.challenges.domain.group import normalize_invite_code
from pit.modules.coaching.application.commands import CheerFriend
from pit.modules.identity.infrastructure.tables import users
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied

MESSAGES_SHOWN = 50

BOARD_TOP = 100  # rows of a group board; the rest is counted, not listed

router = APIRouter(tags=["together"])


@router.post(
    "/me/participations/{participation_id}/group",
    response_model=s.GroupInviteOut,
    dependencies=[Depends(rate_limit("group-create", 20, 3600, per="user"))],
)
async def create_group(
    participation_id: UUID, user_id: UserId, container: ContainerDep
) -> s.GroupInviteOut:
    code: str = await container.bus.handle(
        CreateGroup(user_id=user_id, participation_id=participation_id)
    )
    return s.GroupInviteOut(invite_code=code)


@router.get(
    "/groups/{invite_code}",
    response_model=s.GroupPreviewOut,
    dependencies=[Depends(rate_limit("group-preview", 60, 900))],
)
async def preview(
    invite_code: str, container: ContainerDep, locale: LocaleDep
) -> s.GroupPreviewOut:
    async with container.uow_factory() as uow:
        group = require(
            await uow.groups.get_by_code(normalize_invite_code(invite_code)),
            "Taklif havolasi noto'g'ri yoki eskirgan",
        )
        challenge = require(await uow.challenges.get(group.challenge_id), "Challenge topilmadi")
        owner = require(await uow.users.get(group.owner_id), "Foydalanuvchi topilmadi")
        text = catalog_text(challenge.id, locale)
        return s.GroupPreviewOut(
            invite_code=group.invite_code,
            challenge_title=text.title if text else challenge.title,
            challenge_description=text.description if text else challenge.description,
            category=challenge.category.value,
            duration_days=challenge.duration_days,
            owner=owner.username,
            members=len(group.member_ids),
            week=views.localized_week(s.schedule_to_week(group.schedule), text),
        )


@router.post(
    "/groups/{invite_code}/join",
    response_model=s.IdOut,
    status_code=201,
    dependencies=[Depends(rate_limit("group-join", 10, 3600, per="user"))],
)
async def join(invite_code: str, user_id: UserId, container: ContainerDep) -> s.IdOut:
    participation_id = await container.bus.handle(
        JoinGroup(user_id=user_id, invite_code=invite_code)
    )
    return s.IdOut(id=participation_id)


@router.get("/me/participations/{participation_id}/group", response_model=s.GroupBoardOut | None)
async def board(
    participation_id: UUID, user_id: UserId, container: ContainerDep
) -> s.GroupBoardOut | None:
    """None when this challenge has no group yet."""
    now = container.clock.now()
    async with container.uow_factory() as uow:
        mine = require(await uow.participations.get(participation_id), "Challenge topilmadi")
        if mine.user_id != user_id:
            raise PermissionDenied("Bu sizning challenge'ingiz emas")
        if mine.group_id is None:
            return None
        group = require(await uow.groups.get(mine.group_id), "Guruh topilmadi")
        members = []
        for member_id in await uow.participations.list_in_group(group.id):
            p = require(await uow.participations.get(member_id), "Challenge topilmadi")
            user = require(await uow.users.get(p.user_id), "Foydalanuvchi topilmadi")
            if user.is_erased:
                continue  # left the platform; their name is gone, so is their row
            today = local_date(now, user.timezone)
            members.append(
                s.GroupMemberOut(
                    rank=0,
                    username=user.username,
                    is_me=user.id == user_id,
                    is_owner=user.id == group.owner_id,
                    status=p.status.value,
                    today_status=p.days[today].value if today in p.days else None,
                    current_streak=p.current_streak,
                    best_streak=p.best_streak,
                    days_completed=p.days_completed,
                    total_days=p.total_days,
                )
            )
        members.sort(key=lambda m: (m.days_completed, m.current_streak), reverse=True)
        for place, member in enumerate(members, 1):
            member.rank = place
        # A group can be any size: the top of the board, and me wherever I am.
        shown = [m for m in members if m.rank <= BOARD_TOP or m.is_me]
        return s.GroupBoardOut(invite_code=group.invite_code, size=len(members), members=shown)


@router.post(
    "/me/participations/{participation_id}/group/cheer",
    status_code=204,
    dependencies=[Depends(rate_limit("cheer", 60, 3600, per="user"))],
)
async def cheer(
    participation_id: UUID, body: s.CheerIn, user_id: UserId, container: ContainerDep
) -> None:
    await container.bus.handle(
        CheerFriend(
            user_id=user_id,
            participation_id=participation_id,
            friend_username=body.username,
            emoji=body.emoji,
        )
    )


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    id: UUID
    username: str
    text: str
    created_at: datetime
    is_me: bool


@router.get("/me/participations/{participation_id}/group/messages", response_model=list[MessageOut])
async def group_messages(
    participation_id: UUID, user_id: UserId, container: ContainerDep
) -> list[MessageOut]:
    async with container.uow_factory() as uow:
        participation = require(
            await uow.participations.get(participation_id), "Challenge topilmadi"
        )
        if participation.user_id != user_id:
            raise PermissionDenied("Bu sizning challenge'ingiz emas")
        if participation.group_id is None:
            return []
        messages = await uow.group_messages.recent(participation.group_id, MESSAGES_SHOWN)
        authors = {m.user_id for m in messages}
        rows = await uow.session.execute(
            select(users.c.id, users.c.username).where(users.c.id.in_(authors))
        )
        names = {uid: name for uid, name in rows.tuples()}
        return [
            MessageOut(
                id=m.id,
                username=names.get(m.user_id, "—"),
                text=m.text,
                created_at=m.created_at,
                is_me=m.user_id == user_id,
            )
            for m in messages
        ]


@router.post(
    "/me/participations/{participation_id}/group/messages",
    response_model=s.IdOut,
    status_code=201,
    dependencies=[Depends(rate_limit("group-message", 20, 3600, per="user"))],
)
async def post_group_message(
    participation_id: UUID, body: MessageIn, user_id: UserId, container: ContainerDep
) -> s.IdOut:
    message_id = await container.bus.handle(
        PostGroupMessage(user_id=user_id, participation_id=participation_id, text=body.text)
    )
    return s.IdOut(id=message_id)


@router.post("/me/participations/{participation_id}/share", response_model=s.ShareLinkOut)
async def share_link(
    participation_id: UUID, user_id: UserId, container: ContainerDep
) -> s.ShareLinkOut:
    async with container.uow_factory() as uow:
        mine = require(await uow.participations.get(participation_id), "Challenge topilmadi")
    if mine.user_id != user_id:
        raise PermissionDenied("Bu sizning challenge'ingiz emas")
    return s.ShareLinkOut(token=issue_share_token(participation_id, container.settings))


@router.get(
    "/share/{token}",
    response_model=s.ShareOut,
    dependencies=[Depends(rate_limit("share-view", 120, 60))],
)
async def shared(token: str, container: ContainerDep, locale: LocaleDep) -> s.ShareOut:
    """Public: the page and the picture behind a shared link."""
    try:
        participation_id = read_share_token(token, container.settings)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(404, "Havola topilmadi") from None
    async with container.uow_factory() as uow:
        run = require(await uow.participations.get(participation_id), "Havola topilmadi")
        owner = require(await uow.users.get(run.user_id), "Havola topilmadi")
        challenge = require(await uow.challenges.get(run.challenge_id), "Havola topilmadi")
    if owner.is_erased:
        raise HTTPException(404, "Havola topilmadi")
    text = catalog_text(challenge.id, locale.value)
    return s.ShareOut(
        username=owner.username,
        title=text.title if text else challenge.title,
        category=challenge.category.value,
        status=run.status.value,
        current_streak=run.current_streak,
        best_streak=run.best_streak,
        days_completed=run.days_completed,
        total_days=run.total_days,
    )
