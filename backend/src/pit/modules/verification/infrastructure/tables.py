from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    Uuid,
)

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

proofs = Table(
    "proofs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("participation_id", Uuid, ForeignKey("participations.id"), nullable=False),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("stake_mode", Boolean, nullable=False),
    Column("for_date", Date, nullable=False),
    Column("task_key", String(40), nullable=False),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("file_key", String(300), nullable=True),
    Column("text_note", Text, nullable=True),
    Column("phash", String(64), nullable=True),
    Column("expected_code", String(8), nullable=True),
    Column("status", String(16), nullable=False),
    Column("ai_decision", String(10), nullable=True),
    Column("ai_confidence", Float, nullable=True),
    Column("ai_reason", Text, nullable=True),
    Column("ai_model", String(80), nullable=True),
    Column("ai_detected_code", String(16), nullable=True),
    Column("reviewer_id", Uuid, ForeignKey("users.id"), nullable=True),
    Column("review_approved", Boolean, nullable=True),
    Column("review_note", Text, nullable=True),
    Column("reviewed_at", DateTime(timezone=True), nullable=True),
    *audit_columns(),
    Index("ix_proofs_participation_day", "participation_id", "for_date"),
    Index("ix_proofs_user_phash", "user_id", "phash"),
    Index("ix_proofs_status", "status"),  # moderator queue: status = 'needs_review'
)
