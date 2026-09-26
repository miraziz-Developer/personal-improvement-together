from dataclasses import dataclass
from uuid import UUID

from pit.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PlanDrafted(DomainEvent):
    plan_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class PlanStarted(DomainEvent):
    plan_id: UUID
    user_id: UUID
    participation_id: UUID
