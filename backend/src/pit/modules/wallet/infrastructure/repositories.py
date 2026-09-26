from collections.abc import Mapping
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from pit.modules.wallet.domain.wallet import LedgerTransaction, Wallet
from pit.modules.wallet.infrastructure.tables import (
    ledger_postings,
    ledger_transactions,
    wallets,
)
from pit.shared.domain.money import Money
from pit.shared.infrastructure.repository import Row, SqlRepository, utc


class SqlWalletRepository(SqlRepository[Wallet]):
    table = wallets

    def _to_row(self, item: Wallet) -> Row:
        return {"id": item.id, "available": item.available.amount, "locked": item.locked.amount}

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Wallet:
        return Wallet(id=row["id"], available=Money(row["available"]), locked=Money(row["locked"]))


class SqlLedgerRepository:
    """Append-only. The unique idempotency key in the database is the final guarantee."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pending: list[LedgerTransaction] = []

    def add(self, transaction: LedgerTransaction) -> None:
        self._pending.append(transaction)

    async def has(self, idempotency_key: str) -> bool:
        if any(t.idempotency_key == idempotency_key for t in self._pending):
            return True
        query = select(ledger_transactions.c.id).where(
            ledger_transactions.c.idempotency_key == idempotency_key
        )
        return (await self._session.execute(query)).first() is not None

    async def save_all(self) -> None:
        for tx in self._pending:
            await self._session.execute(
                insert(ledger_transactions).values(
                    id=tx.id,
                    kind=tx.kind.value,
                    user_id=tx.user_id,
                    amount=tx.amount.amount,
                    idempotency_key=tx.idempotency_key,
                    reference_id=tx.reference_id,
                    created_at=utc(tx.created_at),
                )
            )
            await self._session.execute(
                insert(ledger_postings),
                [
                    {
                        "transaction_id": tx.id,
                        "account_kind": p.account.kind.value,
                        "owner_id": p.account.owner_id,
                        "amount": p.amount,
                    }
                    for p in tx.postings
                ],
            )
        self._pending.clear()
