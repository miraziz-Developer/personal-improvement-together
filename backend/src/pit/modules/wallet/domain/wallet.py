"""User money: a cached balance (Wallet) backed by an append-only double-entry ledger.

Every movement is a LedgerTransaction whose postings sum to zero, so money is never
created or destroyed — only moved between accounts. A reconciliation job can rebuild
every wallet from the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvariantViolation
from pit.shared.domain.money import Money


class InsufficientFunds(DomainError):
    code = "insufficient_funds"


class AccountKind(StrEnum):
    USER_AVAILABLE = "user_available"
    USER_LOCKED = "user_locked"
    PLATFORM_REVENUE = "platform_revenue"
    EXTERNAL = "external"  # payment providers: money entering / leaving the platform


@dataclass(frozen=True, slots=True)
class Account:
    kind: AccountKind
    owner_id: UUID | None = None

    @classmethod
    def available(cls, user_id: UUID) -> Account:
        return cls(AccountKind.USER_AVAILABLE, user_id)

    @classmethod
    def locked(cls, user_id: UUID) -> Account:
        return cls(AccountKind.USER_LOCKED, user_id)


PLATFORM_REVENUE = Account(AccountKind.PLATFORM_REVENUE)
EXTERNAL = Account(AccountKind.EXTERNAL)


class TransactionKind(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    STAKE_LOCK = "stake_lock"
    STAKE_RELEASE = "stake_release"
    STAKE_FORFEIT = "stake_forfeit"


@dataclass(frozen=True, slots=True)
class Posting:
    account: Account
    amount: int  # signed: negative = money leaves the account


@dataclass(frozen=True)
class LedgerTransaction:
    kind: TransactionKind
    user_id: UUID
    amount: Money
    idempotency_key: str
    postings: tuple[Posting, ...]
    created_at: datetime
    reference_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if len(self.postings) < 2:
            raise InvariantViolation("Tranzaksiyada kamida ikki yozuv bo'ladi")
        if any(p.amount == 0 for p in self.postings):
            raise InvariantViolation("Nol summali yozuv bo'lmaydi")
        if sum(p.amount for p in self.postings) != 0:
            raise InvariantViolation("Ledger muvozanatda emas")

    @classmethod
    def transfer(
        cls,
        *,
        kind: TransactionKind,
        user_id: UUID,
        amount: Money,
        source: Account,
        destination: Account,
        idempotency_key: str,
        at: datetime,
        reference_id: UUID | None = None,
    ) -> LedgerTransaction:
        return cls(
            kind=kind,
            user_id=user_id,
            amount=amount,
            idempotency_key=idempotency_key,
            postings=(Posting(source, -amount.amount), Posting(destination, amount.amount)),
            created_at=at,
            reference_id=reference_id,
        )


@dataclass(eq=False, kw_only=True)
class Wallet(AggregateRoot):
    """`id` is the owner's user id. `locked` is money frozen in running stake challenges."""

    available: Money
    locked: Money

    @classmethod
    def open(cls, user_id: UUID) -> Wallet:
        return cls(id=user_id, available=Money.zero(), locked=Money.zero())

    def deposit(self, amount: Money, *, idempotency_key: str, at: datetime) -> LedgerTransaction:
        self._require_positive(amount)
        self.available += amount
        return self._tx(
            TransactionKind.DEPOSIT,
            amount,
            EXTERNAL,
            Account.available(self.id),
            idempotency_key,
            at,
        )

    def withdraw(self, amount: Money, *, idempotency_key: str, at: datetime) -> LedgerTransaction:
        self._require_positive(amount)
        self._require_available(amount)
        self.available -= amount
        return self._tx(
            TransactionKind.WITHDRAWAL,
            amount,
            Account.available(self.id),
            EXTERNAL,
            idempotency_key,
            at,
        )

    def lock_stake(
        self, stake: Money, *, participation_id: UUID, idempotency_key: str, at: datetime
    ) -> LedgerTransaction:
        self._require_positive(stake)
        self._require_available(stake)
        self.available -= stake
        self.locked += stake
        return self._tx(
            TransactionKind.STAKE_LOCK,
            stake,
            Account.available(self.id),
            Account.locked(self.id),
            idempotency_key,
            at,
            participation_id,
        )

    def release_stake(
        self, stake: Money, *, participation_id: UUID, idempotency_key: str, at: datetime
    ) -> LedgerTransaction:
        self._require_positive(stake)
        self.locked -= stake
        self.available += stake
        return self._tx(
            TransactionKind.STAKE_RELEASE,
            stake,
            Account.locked(self.id),
            Account.available(self.id),
            idempotency_key,
            at,
            participation_id,
        )

    def forfeit_stake(
        self, stake: Money, *, participation_id: UUID, idempotency_key: str, at: datetime
    ) -> LedgerTransaction:
        self._require_positive(stake)
        self.locked -= stake
        return self._tx(
            TransactionKind.STAKE_FORFEIT,
            stake,
            Account.locked(self.id),
            PLATFORM_REVENUE,
            idempotency_key,
            at,
            participation_id,
        )

    def _require_available(self, amount: Money) -> None:
        if amount > self.available:
            raise InsufficientFunds(f"Hisobingizda mablag' yetarli emas (mavjud: {self.available})")

    @staticmethod
    def _require_positive(amount: Money) -> None:
        if amount.is_zero:
            raise InvariantViolation("Summa noldan katta bo'lishi kerak")

    def _tx(
        self,
        kind: TransactionKind,
        amount: Money,
        source: Account,
        destination: Account,
        idempotency_key: str,
        at: datetime,
        reference_id: UUID | None = None,
    ) -> LedgerTransaction:
        return LedgerTransaction.transfer(
            kind=kind,
            user_id=self.id,
            amount=amount,
            source=source,
            destination=destination,
            idempotency_key=idempotency_key,
            at=at,
            reference_id=reference_id,
        )
