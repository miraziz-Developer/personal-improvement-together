from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from pit.api import schemas as s
from pit.api.deps import ContainerDep, UserId
from pit.modules.wallet.application.commands import Deposit
from pit.modules.wallet.infrastructure.tables import ledger_transactions
from pit.shared.domain.money import Money


async def _stakes_enabled(container: ContainerDep) -> None:
    if not container.settings.stakes_enabled:
        raise HTTPException(404, "Hamyon hozircha yopiq — platforma bepul")


router = APIRouter(tags=["wallet"], dependencies=[Depends(_stakes_enabled)])


@router.get("/wallet", response_model=s.WalletOut)
async def wallet(user_id: UserId, container: ContainerDep) -> s.WalletOut:
    async with container.uow_factory() as uow:
        balance = await uow.wallets.get(user_id)
        rows = await uow.session.execute(
            select(ledger_transactions)
            .where(ledger_transactions.c.user_id == user_id)
            .order_by(ledger_transactions.c.created_at.desc())
            .limit(30)
        )
        return s.WalletOut(
            available=(balance.available if balance else Money.zero()).amount,
            locked=(balance.locked if balance else Money.zero()).amount,
            transactions=[
                s.TransactionOut(
                    id=row["id"],
                    kind=row["kind"],
                    amount=row["amount"],
                    created_at=row["created_at"],
                )
                for row in rows.mappings()
            ],
        )


@router.post("/wallet/dev-deposit", status_code=204)
async def dev_deposit(body: s.DepositIn, user_id: UserId, container: ContainerDep) -> None:
    """Local development only — real money arrives through the Payme/Click webhook."""
    if not container.settings.is_local:
        raise HTTPException(404, "Topilmadi")
    await container.bus.handle(
        Deposit(user_id=user_id, amount=body.amount, provider_ref=f"dev-{uuid4()}")
    )
