from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Table, Uuid, func

from pit.shared.infrastructure.db import metadata

# Source of truth for points. Redis leaderboards can always be rebuilt from this table.
score_entries = Table(
    "score_entries",
    metadata,
    Column("source_key", String(200), primary_key=True),  # makes awarding idempotent
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("points", Integer, nullable=False),
    Column("reason", String(20), nullable=False),
    Column("earned_on", Date, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("ix_score_entries_user_id", "user_id"),
)
