from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Something that happened in the domain.

    Events are the public contract between modules: a downstream module may import an
    upstream module's events, but never its aggregates.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
