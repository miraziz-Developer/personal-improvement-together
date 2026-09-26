"""Web Push (VAPID) through pywebpush. Payloads are encrypted for the browser."""

import asyncio
import json

from pywebpush import WebPushException, webpush

from pit.modules.push.application.ports import PushMessage, SubscriptionGone
from pit.modules.push.domain.subscription import PushSubscription

GONE_STATUSES = {404, 410}  # the browser dropped the subscription


class VapidWebPushSender:
    def __init__(self, *, private_key: str, subject: str) -> None:
        self._private_key = private_key
        self._claims = {"sub": subject}

    async def send(self, subscription: PushSubscription, message: PushMessage) -> None:
        payload = json.dumps(
            {"title": message.title, "body": message.body, "url": message.url},
            ensure_ascii=False,
        )
        info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info=info,
                data=payload,
                vapid_private_key=self._private_key,
                vapid_claims=dict(self._claims),
                timeout=10,
                ttl=24 * 3600,
            )
        except WebPushException as error:
            status = error.response.status_code if error.response is not None else None
            if status in GONE_STATUSES:
                raise SubscriptionGone(str(status)) from None
            raise
