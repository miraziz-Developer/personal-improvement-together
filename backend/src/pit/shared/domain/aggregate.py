from dataclasses import dataclass, field
from uuid import UUID

from pit.shared.domain.events import DomainEvent


@dataclass(eq=False, kw_only=True)
class AggregateRoot:
    """Consistency boundary. Identity-based equality; collects events until they are pulled."""

    id: UUID
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    def __eq__(self, other: object) -> bool:
        return (
            type(other) is type(self) and isinstance(other, AggregateRoot) and other.id == self.id
        )

    def __hash__(self) -> int:
        return hash((type(self), self.id))
