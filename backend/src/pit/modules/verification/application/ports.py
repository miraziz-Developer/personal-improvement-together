from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pit.modules.challenges.domain.challenge import Category
from pit.modules.verification.domain.verdict import AiVerdict


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    proof_id: UUID
    category: Category
    criteria: str  # the challenge's verification_prompt
    file_key: str | None
    text_note: str | None
    expected_code: str | None


class ProofVerifier(Protocol):
    """AI adapter (vision LLM). Must return a structured verdict, never free text."""

    async def verify(self, request: VerificationRequest) -> AiVerdict: ...


class VerificationQueue(Protocol):
    """Hands a proof to a background worker (Celery in production)."""

    async def enqueue(self, proof_id: UUID) -> None: ...
