from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text, Uuid

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

notifications = Table(
    "notifications",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("moment", String(32), nullable=False),
    Column("title", String(200), nullable=False),
    Column("body", Text, nullable=False),
    Column("participation_id", Uuid, ForeignKey("participations.id"), nullable=True),
    Column("subject_id", Uuid, ForeignKey("users.id"), nullable=True),
    Column("sent_at", DateTime(timezone=True), nullable=False),
    Column("read_at", DateTime(timezone=True), nullable=True),
    *audit_columns(),
    Index("ix_notifications_user_feed", "user_id", "sent_at"),
)
