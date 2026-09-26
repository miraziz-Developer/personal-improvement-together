"""What keeps people coming back: the Sunday summary, cheers between friends, badges."""

import pytest

from pit.modules.challenges.application.commands import CreateGroup, JoinGroup
from pit.modules.coaching.application.commands import CheerFriend, SendWeeklySummaries
from pit.modules.coaching.domain.messages import Moment
from pit.modules.identity.domain.user import User
from pit.modules.ranking.domain.achievements import Record, badges_for
from pit.modules.telegram.application.bot import TelegramBot
from pit.modules.telegram.application.ports import Incoming
from pit.shared.domain.errors import DomainError
from tests.application.conftest import World
from tests.fakes import FakeConversation, FakeProofFiles, FakeUnitOfWork


def moments(world: World, user: User) -> list[Moment]:
    return [n.moment for n in world.store.notifications.values() if n.user_id == user.id]


async def until_sunday(world: World, user: User, pid: object, *, prove: bool) -> None:
    """START is a Thursday: live through Friday, Saturday and Sunday."""
    for _ in range(3):
        await world.next_day()
        if prove:
            await world.prove(user, pid)  # type: ignore[arg-type]


async def test_a_strong_week_is_praised(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge())
    await world.prove(user, pid)
    await until_sunday(world, user, pid, prove=True)

    await world.bus.handle(SendWeeklySummaries())
    await world.bus.handle(SendWeeklySummaries())  # a rerun of the job...
    assert moments(world, user).count(Moment.WEEKLY_GREAT) == 1  # ...never sends twice a week


async def test_a_hard_week_gets_support_not_blame(world: World) -> None:
    user = world.add_user()
    # 30 days come with freezes, so two missed days do not end the challenge.
    pid = await world.join(user, world.add_challenge(duration_days=30))
    await world.prove(user, pid)
    await until_sunday(world, user, pid, prove=False)

    await world.bus.handle(SendWeeklySummaries())
    assert Moment.WEEKLY_TOUGH in moments(world, user)


async def friends(world: World) -> tuple[User, User, object, object]:
    owner, friend = world.add_user(), world.add_user()
    owner_pid = await world.join(owner, world.add_challenge())
    code = await world.bus.handle(CreateGroup(user_id=owner.id, participation_id=owner_pid))
    friend_pid = await world.bus.handle(JoinGroup(user_id=friend.id, invite_code=code))
    return owner, friend, owner_pid, friend_pid


async def test_a_friend_can_cheer_once_a_day(world: World) -> None:
    owner, friend, _, friend_pid = await friends(world)
    cheer = CheerFriend(
        user_id=friend.id,
        participation_id=friend_pid,  # type: ignore[arg-type]
        friend_username=owner.username,
    )
    await world.bus.handle(cheer)
    await world.bus.handle(cheer)
    assert moments(world, owner).count(Moment.CHEER) == 1


async def test_only_group_mates_can_be_cheered(world: World) -> None:
    _, friend, _, friend_pid = await friends(world)
    stranger = world.add_user()
    with pytest.raises(DomainError, match="guruhingizda emas"):
        await world.bus.handle(
            CheerFriend(
                user_id=friend.id,
                participation_id=friend_pid,  # type: ignore[arg-type]
                friend_username=stranger.username,
            )
        )


async def test_the_telegram_news_about_a_friend_has_a_cheer_button(world: World) -> None:
    owner, friend, _, friend_pid = await friends(world)
    owner.link_telegram(900)
    await world.prove(friend, friend_pid)  # type: ignore[arg-type]  # owner hears the news

    news = world.telegram.last(900)
    (cheer,) = [c for c in news.callbacks if c.startswith("cheer:")]
    bot = TelegramBot(
        bus=world.bus,
        uow_factory=lambda: FakeUnitOfWork(world.store),
        api=world.telegram,
        conversation=FakeConversation(),
        files=FakeProofFiles(),
        clock=world.clock,
        code_secret=b"test-secret",
        web_url="https://pit.uz",
    )
    await bot.handle(Incoming(chat_id=900, callback_id="cb", callback_data=cheer))
    assert Moment.CHEER in moments(world, friend)
    assert "olqishingizni oldi" in world.telegram.last(900).text


def test_badges_follow_the_record() -> None:
    record = Record(
        days_done=12,
        best_streak=8,
        completed_challenges=1,
        points=300,
        in_group=True,
        telegram_linked=False,
    )
    earned = {badge.key for badge, got in badges_for(record) if got}
    assert earned == {"first_day", "streak_7", "finisher", "together"}
