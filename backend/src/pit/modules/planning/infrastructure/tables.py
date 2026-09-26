from sqlalchemy import Column, ForeignKey, String, Table, Uuid
from sqlalchemy.dialects.postgresql import JSONB

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

plans = Table(
    "plans",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("status", String(10), nullable=False),
    Column("answers", JSONB, nullable=False),  # onboarding answers, kept for future re-plans
    Column("proposal", JSONB, nullable=False),
    Column("challenge_id", Uuid, ForeignKey("challenges.id"), nullable=True),
    Column("participation_id", Uuid, ForeignKey("participations.id"), nullable=True),
    *audit_columns(),
)
