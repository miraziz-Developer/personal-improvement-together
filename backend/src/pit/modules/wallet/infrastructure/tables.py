from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Table,
    Uuid,
)

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

wallets = Table(
    "wallets",
    metadata,
    Column("id", Uuid, ForeignKey("users.id"), primary_key=True),  # = user id
    Column("available", BigInteger, nullable=False),
    Column("locked", BigInteger, nullable=False),
    *audit_columns(),
    # Last line of defence: even a bug cannot make a balance negative.
    CheckConstraint("available >= 0", name="available_non_negative"),
    CheckConstraint("locked >= 0", name="locked_non_negative"),
)

# Append-only. Never updated, never deleted.
ledger_transactions = Table(
    "ledger_transactions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("kind", String(20), nullable=False),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("amount", BigInteger, nullable=False),
    Column("idempotency_key", String(120), nullable=False, unique=True),
    Column("reference_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("amount > 0", name="amount_positive"),
)

ledger_postings = Table(
    "ledger_postings",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("transaction_id", Uuid, ForeignKey("ledger_transactions.id"), nullable=False),
    Column("account_kind", String(20), nullable=False),
    Column("owner_id", Uuid, nullable=True),
    Column("amount", BigInteger, nullable=False),  # signed
)
