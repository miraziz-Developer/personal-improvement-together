"""seed regions of Uzbekistan

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25

Ids are uuid5("pit:region:<slug>") so they are stable across every environment.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REGIONS = [
    ("karakalpakstan", "Qoraqalpog'iston Respublikasi", "Республика Каракалпакстан"),
    ("andijan", "Andijon viloyati", "Андижанская область"),
    ("bukhara", "Buxoro viloyati", "Бухарская область"),
    ("fergana", "Farg'ona viloyati", "Ферганская область"),
    ("jizzakh", "Jizzax viloyati", "Джизакская область"),
    ("khorezm", "Xorazm viloyati", "Хорезмская область"),
    ("namangan", "Namangan viloyati", "Наманганская область"),
    ("navoi", "Navoiy viloyati", "Навоийская область"),
    ("kashkadarya", "Qashqadaryo viloyati", "Кашкадарьинская область"),
    ("samarkand", "Samarqand viloyati", "Самаркандская область"),
    ("syrdarya", "Sirdaryo viloyati", "Сырдарьинская область"),
    ("surkhandarya", "Surxondaryo viloyati", "Сурхандарьинская область"),
    ("tashkent-region", "Toshkent viloyati", "Ташкентская область"),
    ("tashkent", "Toshkent shahri", "город Ташкент"),
]


def region_id(slug: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"pit:region:{slug}")


regions = sa.table(
    "regions",
    sa.column("id", sa.Uuid),
    sa.column("name_uz", sa.String),
    sa.column("name_ru", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        regions,
        [{"id": region_id(slug), "name_uz": uz, "name_ru": ru} for slug, uz, ru in REGIONS],
    )


def downgrade() -> None:
    op.execute(regions.delete().where(regions.c.id.in_([region_id(s) for s, _, _ in REGIONS])))
