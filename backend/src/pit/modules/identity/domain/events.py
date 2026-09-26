from dataclasses import dataclass
from uuid import UUID

from pit.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: UUID
    birth_year: int
    region_id: UUID


@dataclass(frozen=True, kw_only=True)
class PhoneVerified(DomainEvent):
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class AccountErased(DomainEvent):
    """Every module forgets what it holds about this user (photos, notes, notifications...)."""

    user_id: UUID
