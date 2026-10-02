"""bonus freezes for bringing friends

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-02 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "participations",
        sa.Column("bonus_freezes", sa.SmallInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("participations", "bonus_freezes")
