from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pit.modules.wallet.domain.wallet import (
    Account,
    AccountKind,
    InsufficientFunds,
    LedgerTransaction,
    Posting,
    TransactionKind,
    Wallet,
)
from pit.shared.domain.errors import InvariantViolation
from pit.shared.domain.money import Money

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def funded(amount: int) -> Wallet:
    wallet = Wallet.open(uuid4())
    wallet.deposit(Money(amount), idempotency_key="d", at=NOW)
    return wallet


def test_every_transaction_is_balanced() -> None:
    tx = funded(100).lock_stake(Money(60), participation_id=uuid4(), idempotency_key="l", at=NOW)
    assert sum(p.amount for p in tx.postings) == 0
    assert tx.kind is TransactionKind.STAKE_LOCK


def test_unbalanced_transaction_is_impossible() -> None:
    with pytest.raises(InvariantViolation):
        LedgerTransaction(
            kind=TransactionKind.DEPOSIT,
            user_id=uuid4(),
            amount=Money(10),
            idempotency_key="x",
            postings=(
                Posting(Account(AccountKind.EXTERNAL), -10),
                Posting(Account(AccountKind.PLATFORM_REVENUE), 9),
            ),
            created_at=NOW,
        )


def test_lock_release_forfeit_move_money_between_buckets() -> None:
    wallet = funded(100_000)
    pid = uuid4()
    wallet.lock_stake(Money(80_000), participation_id=pid, idempotency_key="l", at=NOW)
    assert (wallet.available, wallet.locked) == (Money(20_000), Money(80_000))

    wallet.release_stake(Money(30_000), participation_id=pid, idempotency_key="r", at=NOW)
    assert (wallet.available, wallet.locked) == (Money(50_000), Money(50_000))

    tx = wallet.forfeit_stake(Money(50_000), participation_id=pid, idempotency_key="f", at=NOW)
    assert (wallet.available, wallet.locked) == (Money(50_000), Money.zero())
    assert tx.postings[1].account.kind is AccountKind.PLATFORM_REVENUE


def test_cannot_lock_more_than_available() -> None:
    with pytest.raises(InsufficientFunds):
        funded(10_000).lock_stake(
            Money(10_001), participation_id=uuid4(), idempotency_key="l", at=NOW
        )


def test_money_is_whole_and_non_negative() -> None:
    with pytest.raises(InvariantViolation):
        Money(-1)
    with pytest.raises(InvariantViolation):
        Money(1.5)  # type: ignore[arg-type]
    with pytest.raises(InvariantViolation):
        Money(5) - Money(6)
    assert str(Money(100_000)) == "100 000 so'm"
