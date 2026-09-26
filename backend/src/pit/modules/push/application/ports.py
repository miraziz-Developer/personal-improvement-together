from dataclasses import dataclass
from typing import Protocol

from pit.modules.push.domain.subscription import PushSubscription


@dataclass(frozen=True, slots=True)
class PushMessage:
    title: str
    body: str
    url: str  # where a tap on the notification leads


class SubscriptionGone(Exception):
    """The browser unsubscribed or the subscription expired: forget it."""


class WebPushSender(Protocol):
    async def send(self, subscription: PushSubscription, message: PushMessage) -> None: ...
