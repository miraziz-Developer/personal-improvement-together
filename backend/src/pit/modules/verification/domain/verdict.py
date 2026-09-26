from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pit.shared.domain.errors import InvariantViolation


class ProofStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class AiDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class AiVerdict:
    decision: AiDecision
    confidence: float
    reason: str
    model: str
    detected_code: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvariantViolation("AI ishonch darajasi 0 va 1 oralig'ida bo'lishi kerak")


@dataclass(frozen=True, slots=True)
class HumanReview:
    reviewer_id: UUID
    approved: bool
    note: str
    reviewed_at: datetime
