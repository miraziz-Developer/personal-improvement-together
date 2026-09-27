"""life plans

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-27 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "life_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("duration_days", sa.SmallInteger(), nullable=False),
        sa.Column("frame", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("goals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_life_plans_user_id"), "life_plans", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_life_plans_user_id"), table_name="life_plans")
    op.drop_table("life_plans")
