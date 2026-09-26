from typing import Protocol
from uuid import UUID

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.events import (
    ParticipationCancelled,
    ParticipationCompleted,
    ParticipationFailed,
)
from pit.modules.wallet.application.commands import Deposit
from pit.modules.wallet.domain.repositories import LedgerRepository, WalletRepository
from pit.modules.wallet.domain.wallet import InsufficientFunds, Wallet
from pit.shared.application.clock import Clock
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.money import Money


class WalletUoW(Transaction, Protocol):
    @property
    def wallets(self) -> WalletRepository: ...

    @property
    def ledger(self) -> LedgerRepository: ...


class WalletStakeEscrow:
    """Implements the challenges module's StakeEscrow port inside the caller's transaction."""

    def __init__(self, uow: WalletUoW, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def lock(self, *, user_id: UUID, participation_id: UUID, stake: Money) -> None:
        key = f"stake-lock:{participation_id}"
        if await self._uow.ledger.has(key):
            return
        wallet = await self._uow.wallets.get(user_id)
        if wallet is None:
            raise InsufficientFunds("Hisobingizda mablag' yo'q. Avval hisobni to'ldiring")
        self._uow.ledger.add(
            wallet.lock_stake(
                stake, participation_id=participation_id, idempotency_key=key, at=self._clock.now()
            )
        )


async def deposit(cmd: Deposit, uow: WalletUoW, *, clock: Clock) -> None:
    key = f"deposit:{cmd.provider_ref}"
    async with uow:
        if await uow.ledger.has(key):
            return
        wallet = await uow.wallets.get(cmd.user_id)
        if wallet is None:
            wallet = Wallet.open(cmd.user_id)
            uow.wallets.add(wallet)
        uow.ledger.add(wallet.deposit(Money(cmd.amount), idempotency_key=key, at=clock.now()))
        await uow.commit()


async def release_stake(
    event: ParticipationCompleted | ParticipationCancelled, uow: WalletUoW, *, clock: Clock
) -> None:
    if event.mode is not ParticipationMode.STAKE:
        return
    key = f"stake-release:{event.participation_id}"
    async with uow:
        if await uow.ledger.has(key):
            return
        wallet = require(await uow.wallets.get(event.user_id), "Hisob topilmadi")
        uow.ledger.add(
            wallet.release_stake(
                event.stake,
                participation_id=event.participation_id,
                idempotency_key=key,
                at=clock.now(),
            )
        )
        await uow.commit()


async def forfeit_stake(event: ParticipationFailed, uow: WalletUoW, *, clock: Clock) -> None:
    if event.mode is not ParticipationMode.STAKE:
        return
    key = f"stake-forfeit:{event.participation_id}"
    async with uow:
        if await uow.ledger.has(key):
            return
        wallet = require(await uow.wallets.get(event.user_id), "Hisob topilmadi")
        uow.ledger.add(
            wallet.forfeit_stake(
                event.stake,
                participation_id=event.participation_id,
                idempotency_key=key,
                at=clock.now(),
            )
        )
        await uow.commit()
