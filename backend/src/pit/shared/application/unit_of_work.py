from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from types import TracebackType
from typing import Any, Protocol, Self

from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.events import DomainEvent


class UnitOfWork(ABC):
    """One business transaction.

    Events are harvested only from committed work, so a rolled-back change never
    triggers side effects in other modules.
    """

    def __init__(self) -> None:
        self._committed_events: list[DomainEvent] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.rollback()

    async def commit(self) -> None:
        await self._commit()
        for aggregate in self._seen_aggregates():
            self._committed_events.extend(aggregate.pull_events())

    def collect_new_events(self) -> list[DomainEvent]:
        events, self._committed_events = self._committed_events, []
        return events

    @abstractmethod
    async def _commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    def _seen_aggregates(self) -> Iterable[AggregateRoot]: ...


class Transaction(Protocol):
    """What application handlers need from a unit of work, besides its repositories.
    Module-specific protocols extend it and expose repositories as read-only properties."""

    async def __aenter__(self) -> Any: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
