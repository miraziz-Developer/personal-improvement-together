"""Together: invite friends, same plan, group news through the coach."""

from uuid import UUID

import pytest

from pit.modules.challenges.application.commands import (
    ChangeSchedule,
    CreateGroup,
    JoinChallenge,
    JoinGroup,
)
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.group import MAX_GROUP_MEMBERS, Group
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.coaching.domain.messages import Moment
from pit.modules.identity.domain.user import User
from pit.shared.domain.errors import DomainError, PermissionDenied
from tests.application.conftest import World


async def invite(world: World, owner: User, participation_id: UUID) -> str:
    code: str = await world.bus.handle(
        CreateGroup(user_id=owner.id, participation_id=participation_id)
    )
    return code


async def accept(world: World, friend: User, code: str) -> UUID:
    participation_id: UUID = await world.bus.handle(JoinGroup(user_id=friend.id, invite_code=code))
    return participation_id


def group_of(world: World, participation_id: UUID) -> Group:
    group_id = world.participation(participation_id).group_id
    assert group_id is not None
    return world.store.groups[group_id]


def news(world: World, user: User, moment: Moment) -> list[str]:
    return [
        n.title
        for n in world.store.notifications.values()
        if n.user_id == user.id and n.moment == moment
    ]


async def test_invite_code_is_created_once(world: World) -> None:
    owner = world.add_user()
    pid = await world.join(owner, world.add_challenge())
    code = await invite(world, owner, pid)
    assert len(code) == 8 and await invite(world, owner, pid) == code
    assert group_of(world, pid).member_ids == [owner.id]


async def test_friend_joins_with_the_owners_current_plan(world: World) -> None:
    owner, friend = world.add_user(), world.add_user()
    pid = await world.join(owner, world.add_challenge())
    harder = Schedule.every_day(TaskSpec(key="main", title="Sport zali", minutes=90))
    await world.bus.handle(ChangeSchedule(user_id=owner.id, participation_id=pid, schedule=harder))

    code = await invite(world, owner, pid)
    friend_pid = await accept(world, friend, code.lower())  # codes are case-insensitive

    joined = world.participation(friend_pid)
    assert joined.current_schedule == world.participation(pid).current_schedule
    assert joined.group_id == world.participation(pid).group_id
    assert joined.mode is ParticipationMode.FREE
    assert group_of(world, pid).member_ids == [owner.id, friend.id]


async def test_joining_twice_or_a_full_group_is_refused(world: World) -> None:
    owner = world.add_user()
    code = await invite(world, owner, await world.join(owner, world.add_challenge()))
    friend = world.add_user()
    await accept(world, friend, code)
    with pytest.raises(DomainError, match="allaqachon"):
        await accept(world, friend, code)

    for _ in range(MAX_GROUP_MEMBERS - 2):
        await accept(world, world.add_user(), code)
    with pytest.raises(DomainError, match="to'lgan"):
        await accept(world, world.add_user(), code)


async def test_unknown_code_is_refused(world: World) -> None:
    with pytest.raises(DomainError, match="Taklif havolasi"):
        await accept(world, world.add_user(), "ABCDEFGH")


async def test_a_personal_challenge_is_joined_only_through_an_invite(world: World) -> None:
    owner, stranger = world.add_user(), world.add_user()
    personal: Challenge = world.add_challenge()
    personal.is_template, personal.created_by = False, owner.id
    pid = await world.join(owner, personal)

    with pytest.raises(PermissionDenied):
        await world.bus.handle(
            JoinChallenge(
                user_id=stranger.id, challenge_id=personal.id, mode=ParticipationMode.FREE
            )
        )
    await accept(world, stranger, await invite(world, owner, pid))  # the invite works


async def test_the_group_hears_about_new_friends_and_their_days(world: World) -> None:
    owner, friend = world.add_user(), world.add_user()
    pid = await world.join(owner, world.add_challenge())
    friend_pid = await accept(world, friend, await invite(world, owner, pid))
    assert news(world, owner, Moment.FRIEND_JOINED)

    await world.prove(friend, friend_pid)
    assert len(news(world, owner, Moment.FRIEND_DAY_DONE)) == 1
    assert not news(world, friend, Moment.FRIEND_DAY_DONE)  # nobody is told about themselves


async def test_a_friend_who_blocked_telegram_still_gets_site_notifications(
    world: World,
) -> None:
    owner, friend = world.add_user(), world.add_user()
    pid = await world.join(owner, world.add_challenge())
    friend_pid = await accept(world, friend, await invite(world, owner, pid))
    world.telegram.down = True  # Telegram trouble must not lose the in-app news
    await world.prove(friend, friend_pid)
    assert news(world, owner, Moment.FRIEND_DAY_DONE)
