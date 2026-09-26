from sqlalchemy import Column, ForeignKey, Index, String, Table, Text, Uuid

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

push_subscriptions = Table(
    "push_subscriptions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("endpoint", Text, nullable=False, unique=True),
    Column("p256dh", String(200), nullable=False),
    Column("auth", String(100), nullable=False),
    *audit_columns(),
    Index("ix_push_subscriptions_user", "user_id"),
)
