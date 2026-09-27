from sqlalchemy import Column, ForeignKey, SmallInteger, String, Table, Uuid
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

life_plans = Table(
    "life_plans",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False, index=True),
    Column("status", String(10), nullable=False),
    Column("language", String(2), nullable=False),
    Column("duration_days", SmallInteger, nullable=False),
    Column("frame", JSONB, nullable=False),  # wake, sleep, busy blocks
    Column("goals", JSONB, nullable=False),  # answers + proposal (+ started ids) per goal
    *audit_columns(),
)
