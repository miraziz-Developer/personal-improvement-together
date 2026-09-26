from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    Uuid,
)

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

regions = Table(
    "regions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name_uz", String(80), nullable=False),
    Column("name_ru", String(80), nullable=False),
    Column("parent_id", Uuid, ForeignKey("regions.id"), nullable=True),
)

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("username", String(30), nullable=False, unique=True),
    Column("birth_date", Date, nullable=False),
    Column("region_id", Uuid, ForeignKey("regions.id"), nullable=False),
    Column("timezone", String(64), nullable=False),
    Column("phone", String(13), nullable=True),
    Column("phone_verified", Boolean, nullable=False),
    Column("role", String(16), nullable=False),
    Column("password_hash", String(255), nullable=False, server_default=""),
    Column("terms_version", String(20), nullable=True),
    Column("terms_accepted_at", DateTime(timezone=True), nullable=True),
    Column("telegram_chat_id", BigInteger, nullable=True),
    Column("google_sub", String(255), nullable=True, unique=True),
    Column("email", String(255), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("locale", String(2), nullable=False, server_default="uz"),
    *audit_columns(),
    # Deferred: moving a chat between accounts unlinks one and links the other in a single
    # transaction, in whatever order the updates are flushed.
    UniqueConstraint(
        "telegram_chat_id",
        name="uq_users_telegram_chat_id",
        deferrable=True,
        initially="DEFERRED",
    ),
)
