"""Base for SQL repositories: identity map, dirty checking and optimistic locking.

Aggregates are plain Python objects mutated in place by the domain. The repository keeps
a snapshot of each loaded aggregate's row; on commit it writes only what changed, with
`WHERE version = <loaded version>`. If another transaction got there first, nothing is
updated and ConcurrencyConflict is raised — the message bus then retries with fresh state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, Table, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.domain.aggregate import AggregateRoot

type Row = dict[str, Any]


def audit_columns() -> list[Column[Any]]:
    return [
        Column("version", Integer, nullable=False),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    ]


def utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC)


class SqlRepository[T: AggregateRoot](ABC):
    table: Table

    def __init__(self, session: AsyncSession, seen: set[AggregateRoot]) -> None:
        self._session = session
        self._seen = seen
        self._new: dict[UUID, T] = {}
        # id -> (aggregate, version at load time, row snapshot, children snapshot)
        self._loaded: dict[UUID, tuple[T, int, Row, Any]] = {}

    # --- mapping, implemented per aggregate ---------------------------------------------

    @abstractmethod
    def _to_row(self, item: T) -> Row: ...

    @abstractmethod
    async def _to_aggregate(self, row: Mapping[str, Any]) -> T: ...

    def _children(self, item: T) -> Any:
        """Comparable snapshot of child rows (e.g. participation days). None = no children."""
        return None

    async def _save_children(self, item: T) -> None:
        return None

    # --- repository protocol --------------------------------------------------------------

    def add(self, item: T) -> None:
        self._new[item.id] = item
        self._seen.add(item)

    async def get(self, item_id: UUID) -> T | None:
        if item_id in self._new:
            return self._new[item_id]
        if item_id in self._loaded:
            return self._loaded[item_id][0]
        items = await self._select(self.table.c.id == item_id)
        return items[0] if items else None

    # --- helpers for subclasses -------------------------------------------------------

    async def _select(self, *where: ColumnElement[bool]) -> list[T]:
        rows = (await self._session.execute(select(self.table).where(*where))).mappings().all()
        return [await self._track(dict(row)) for row in rows]

    def _pending(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self._new.values() if predicate(item)]

    async def _exists(self, *where: ColumnElement[bool]) -> bool:
        query = select(self.table.c.id).where(*where).limit(1)
        return (await self._session.execute(query)).first() is not None

    async def _track(self, row: Mapping[str, Any]) -> T:
        item_id: UUID = row["id"]
        if item_id in self._loaded:
            return self._loaded[item_id][0]
        item = await self._to_aggregate(row)
        self._loaded[item_id] = (item, row["version"], self._to_row(item), self._children(item))
        self._seen.add(item)
        return item

    # --- unit of work -----------------------------------------------------------------

    async def save_all(self) -> None:
        for item in self._new.values():
            await self._session.execute(insert(self.table).values(**self._to_row(item), version=1))
            await self._save_children(item)
        for item_id, (item, version, row_snapshot, children_snapshot) in self._loaded.items():
            row, children = self._to_row(item), self._children(item)
            if row == row_snapshot and children == children_snapshot:
                continue  # untouched: readers never conflict with each other
            result = await self._session.execute(
                update(self.table)
                .where(self.table.c.id == item_id, self.table.c.version == version)
                .values(**row, version=version + 1)
            )
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise ConcurrencyConflict(f"{self.table.name} {item_id} was changed concurrently")
            if children != children_snapshot:
                await self._save_children(item)

    async def _replace_children(
        self, table: Table, fk: str, parent_id: UUID, rows: list[Row]
    ) -> None:
        await self._session.execute(delete(table).where(table.c[fk] == parent_id))
        if rows:
            await self._session.execute(insert(table), rows)
