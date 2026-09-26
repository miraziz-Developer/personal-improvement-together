from dataclasses import dataclass
from datetime import date
from uuid import UUID

from pit.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ProofSubmitted(DomainEvent):
    proof_id: UUID
    participation_id: UUID


@dataclass(frozen=True, kw_only=True)
class ProofApproved(DomainEvent):
    proof_id: UUID
    participation_id: UUID
    user_id: UUID
    day: date
    task_key: str
    by_human: bool


@dataclass(frozen=True, kw_only=True)
class ProofRejected(DomainEvent):
    proof_id: UUID
    participation_id: UUID
    user_id: UUID
    day: date
    task_key: str
    by_human: bool
    reason: str


@dataclass(frozen=True, kw_only=True)
class ProofSentToReview(DomainEvent):
    proof_id: UUID
    participation_id: UUID
    day: date
    task_key: str
