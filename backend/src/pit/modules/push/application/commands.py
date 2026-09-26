from dataclasses import dataclass
from uuid import UUID

from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class SubscribePush(Command):
    user_id: UUID
    endpoint: str
    p256dh: str
    auth: str


@dataclass(frozen=True, kw_only=True)
class UnsubscribePush(Command):
    user_id: UUID
    endpoint: str
