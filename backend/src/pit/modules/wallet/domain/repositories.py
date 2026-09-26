from typing import Protocol
from uuid import UUID

from pit.modules.wallet.domain.wallet import LedgerTransaction, Wallet


class WalletRepository(Protocol):
    def add(self, wallet: Wallet) -> None: ...

    async def get(self, user_id: UUID) -> Wallet | None: ...


class LedgerRepository(Protocol):
    """Append-only. `idempotency_key` is unique — the same money movement is never applied twice."""

    def add(self, transaction: LedgerTransaction) -> None: ...

    async def has(self, idempotency_key: str) -> bool: ...
