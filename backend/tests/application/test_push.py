"""Browser push: the coach's messages reach subscribed browsers."""

from pit.modules.identity.application.commands import EraseAccount
from pit.modules.identity.domain.user import User
from pit.modules.push.application.commands import SubscribePush, UnsubscribePush
from tests.application.conftest import World
from tests.fakes import FakePush

PHONE = "https://fcm.googleapis.com/fcm/send/phone"
LAPTOP = "https://updates.push.services.mozilla.com/wpush/v2/laptop"


def pushes(world: World) -> FakePush:
    assert isinstance(world.deps.push, FakePush)
    return world.deps.push


async def subscribe(world: World, user: User, endpoint: str) -> None:
    await world.bus.handle(
        SubscribePush(user_id=user.id, endpoint=endpoint, p256dh="key", auth="secret")
    )


async def test_coach_messages_reach_every_browser_of_the_user(world: World) -> None:
    user = world.add_user()
    await subscribe(world, user, PHONE)
    await subscribe(world, user, LAPTOP)
    pid = await world.join(user, world.add_challenge())

    sent = pushes(world).sent
    assert {endpoint for endpoint, _ in sent} == {PHONE, LAPTOP}
    assert all(message.url == f"/c/{pid}" for _, message in sent)


async def test_an_expired_subscription_is_forgotten(world: World) -> None:
    user = world.add_user()
    await subscribe(world, user, PHONE)
    pushes(world).gone.add(PHONE)
    await world.join(user, world.add_challenge())
    assert not world.store.push_subscriptions


async def test_the_browser_follows_whoever_signed_in_last(world: World) -> None:
    first, second = world.add_user(), world.add_user()
    await subscribe(world, first, PHONE)
    await subscribe(world, second, PHONE)
    (subscription,) = world.store.push_subscriptions.values()
    assert subscription.user_id == second.id

    await world.bus.handle(UnsubscribePush(user_id=first.id, endpoint=PHONE))  # not theirs
    assert world.store.push_subscriptions


async def test_erasing_the_account_drops_its_subscriptions(world: World) -> None:
    user = world.add_user()
    await subscribe(world, user, PHONE)
    await world.bus.handle(EraseAccount(user_id=user.id, confirm_username=user.username))
    assert not world.store.push_subscriptions
