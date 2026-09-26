from dataclasses import dataclass
from uuid import UUID

from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class Deposit(Command):
    """Sent by the payment-provider webhook after the provider confirms the payment."""

    user_id: UUID
    amount: int
    provider_ref: str  # provider's transaction id — makes webhook retries harmless
