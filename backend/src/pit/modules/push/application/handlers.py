"""Browser notifications: one more delivery channel for what the coach says."""

import logging
from typing import Protocol
from uuid import uuid4

from pit.modules.coaching.domain.notification import NotificationCreated
from pit.modules.coaching.domain.repositories import NotificationRepository
from pit.modules.identity.domain.events import AccountErased
from pit.modules.push.application.commands import SubscribePush, UnsubscribePush
from pit.modules.push.application.ports import PushMessage, SubscriptionGone, WebPushSender
from pit.modules.push.domain.subscription import PushSubscription, PushSubscriptionRepository
from pit.shared.application.clock import Clock
from pit.shared.application.unit_of_work import Transaction

logger = logging.getLogger(__name__)


class PushUoW(Transaction, Protocol):
    @property
    def push_subscriptions(self) -> PushSubscriptionRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...


async def subscribe(cmd: SubscribePush, uow: PushUoW, *, clock: Clock) -> None:
    async with uow:
        existing = await uow.push_subscriptions.get_by_endpoint(cmd.endpoint)
        if existing is not None:
            existing.move_to(cmd.user_id, p256dh=cmd.p256dh, auth=cmd.auth)
        else:
            uow.push_subscriptions.add(
                PushSubscription(
                    id=uuid4(),
                    user_id=cmd.user_id,
                    endpoint=cmd.endpoint,
                    p256dh=cmd.p256dh,
                    auth=cmd.auth,
                    created_at=clock.now(),
                )
            )
        await uow.commit()


async def unsubscribe(cmd: UnsubscribePush, uow: PushUoW) -> None:
    async with uow:
        existing = await uow.push_subscriptions.get_by_endpoint(cmd.endpoint)
        if existing is not None and existing.user_id == cmd.user_id:
            await uow.push_subscriptions.remove(existing)
            await uow.commit()


async def deliver_push(event: NotificationCreated, uow: PushUoW, *, sender: WebPushSender) -> None:
    """Best effort, like Telegram: a push failure never breaks the platform's own work."""
    async with uow:
        subscriptions = await uow.push_subscriptions.list_for_user(event.user_id)
        if not subscriptions:
            return
        notification = await uow.notifications.get(event.notification_id)
        if notification is None:
            return
        path = f"/c/{notification.participation_id}" if notification.participation_id else "/"
        message = PushMessage(title=notification.title, body=notification.body, url=path)
        gone = False
        for subscription in subscriptions:
            try:
                await sender.send(subscription, message)
            except SubscriptionGone:
                await uow.push_subscriptions.remove(subscription)
                gone = True
            except Exception:
                logger.warning("Web push to %s failed", subscription.id, exc_info=True)
        if gone:
            await uow.commit()


async def forget_subscriptions(event: AccountErased, uow: PushUoW) -> None:
    async with uow:
        for subscription in await uow.push_subscriptions.list_for_user(event.user_id):
            await uow.push_subscriptions.remove(subscription)
        await uow.commit()
