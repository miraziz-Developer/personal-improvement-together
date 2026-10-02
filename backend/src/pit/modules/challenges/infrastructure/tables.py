from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from pit.shared.infrastructure.db import metadata
from pit.shared.infrastructure.repository import audit_columns

challenges = Table(
    "challenges",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("description", Text, nullable=False),
    Column("category", String(20), nullable=False),
    Column("duration_days", SmallInteger, nullable=False),
    Column("difficulty", SmallInteger, nullable=False),
    Column("proof_types", JSONB, nullable=False),
    Column("verification_prompt", Text, nullable=False),
    Column("stake_allowed", Boolean, nullable=False),
    Column("min_stake", BigInteger, nullable=False),
    Column("max_stake", BigInteger, nullable=False),
    Column("default_schedule", JSONB, nullable=False),
    Column("roadmap", JSONB, nullable=True),
    Column("is_template", Boolean, nullable=False),
    Column("approval_status", String(16), nullable=False),
    Column("created_by", Uuid, ForeignKey("users.id"), nullable=True),
    *audit_columns(),
)

participations = Table(
    "participations",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("challenge_id", Uuid, ForeignKey("challenges.id"), nullable=False),
    Column("mode", String(8), nullable=False),
    Column("stake", BigInteger, nullable=False),
    Column("difficulty", SmallInteger, nullable=False),
    Column("start_date", Date, nullable=False),
    Column("duration_days", SmallInteger, nullable=False),
    Column("status", String(16), nullable=False),
    # [{"since": "2026-10-01", "week": [[task, ...] x 7]}] — past days keep their plan
    Column("schedule_history", JSONB, nullable=False),
    Column("freezes_total", SmallInteger, nullable=False),
    Column("freezes_used", SmallInteger, nullable=False),
    Column("bonus_freezes", SmallInteger, nullable=False, server_default="0"),
    Column("paused_days", SmallInteger, nullable=False, server_default="0"),
    Column("current_streak", Integer, nullable=False),
    Column("best_streak", Integer, nullable=False),
    Column("group_id", Uuid, nullable=True),
    Column("finished_on", Date, nullable=True),
    *audit_columns(),
    CheckConstraint("stake >= 0", name="stake_non_negative"),
    # The database, not just the domain, guarantees one open run per user and challenge.
    Index(
        "uq_participations_one_open_run",
        "user_id",
        "challenge_id",
        unique=True,
        postgresql_where=text("status IN ('scheduled', 'active')"),
    ),
    Index("ix_participations_status", "status"),
    Index("ix_participations_group", "group_id"),
)

# "Together": friends on one challenge with the owner's plan, joined by invite code.
groups = Table(
    "groups",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("challenge_id", Uuid, ForeignKey("challenges.id"), nullable=False),
    Column("owner_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("invite_code", String(8), nullable=False, unique=True),
    Column("schedule", JSONB, nullable=False),
    Column("member_ids", JSONB, nullable=False),  # ["uuid", ...] in joining order
    *audit_columns(),
)

participation_days = Table(
    "participation_days",
    metadata,
    Column(
        "participation_id",
        Uuid,
        ForeignKey("participations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("day", Date, primary_key=True),
    Column("status", String(16), nullable=False),
)

group_messages = Table(
    "group_messages",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("group_id", Uuid, ForeignKey("groups.id"), nullable=False),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("text", String(280), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_group_messages_group_time", "group_id", "created_at"),
)
