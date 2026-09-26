"""Together: invite friends to a challenge, see how the group is doing."""

from uuid import UUID

from fastapi import APIRouter, Depends

from pit.api import schemas as s
from pit.api.deps import ContainerDep, UserId
from pit.api.ratelimit import rate_limit
from pit.modules.challenges.application.commands import CreateGroup, JoinGroup
from pit.modules.challenges.domain.group import normalize_invite_code
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require
from pit.shared.domain.errors import PermissionDenied

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
async def preview(invite_code: str, container: ContainerDep) -> s.GroupPreviewOut:
    async with container.uow_factory() as uow:
        group = require(
            await uow.groups.get_by_code(normalize_invite_code(invite_code)),
            "Taklif havolasi noto'g'ri yoki eskirgan",
        )
        challenge = require(await uow.challenges.get(group.challenge_id), "Challenge topilmadi")
        owner = require(await uow.users.get(group.owner_id), "Foydalanuvchi topilmadi")
        return s.GroupPreviewOut(
            invite_code=group.invite_code,
            challenge_title=challenge.title,
            challenge_description=challenge.description,
            category=challenge.category.value,
            duration_days=challenge.duration_days,
            owner=owner.username,
            members=len(group.member_ids),
            is_full=group.is_full,
            week=s.schedule_to_week(group.schedule),
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
            today = local_date(now, user.timezone)
            members.append(
                s.GroupMemberOut(
                    username=user.username,
                    is_me=user.id == user_id,
                    is_owner=user.id == group.owner_id,
                    status=p.status.value,
                    today_status=p.days[today].value if today in p.days else None,
                    current_streak=p.current_streak,
                    best_streak=p.best_streak,
                    days_completed=p.days_completed,
                    total_days=len(p.days),
                )
            )
        members.sort(key=lambda m: (m.days_completed, m.current_streak), reverse=True)
        return s.GroupBoardOut(invite_code=group.invite_code, members=members)
