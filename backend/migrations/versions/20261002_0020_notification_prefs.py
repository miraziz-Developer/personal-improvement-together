"""notification preferences

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-02 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("remind_before", sa.SmallInteger(), server_default="10", nullable=False)
    )
    op.add_column("users", sa.Column("quiet_from", sa.Time(), nullable=True))
    op.add_column("users", sa.Column("quiet_to", sa.Time(), nullable=True))
    op.add_column(
        "users", sa.Column("friends_news", sa.Boolean(), server_default="true", nullable=False)
    )


def downgrade() -> None:
    for column in ("friends_news", "quiet_to", "quiet_from", "remind_before"):
        op.drop_column("users", column)
