from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text, Uuid, text

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

reports = Table(
    "reports",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("reporter_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("reported_user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("reason", String(16), nullable=False),
    Column("details", Text, nullable=False),
    Column("status", String(16), nullable=False),
    Column("resolved_by", Uuid, ForeignKey("users.id"), nullable=True),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    *audit_columns(),
    Index("ix_reports_open", "created_at", postgresql_where=text("status = 'open'")),
)
