from datetime import date
from typing import Protocol
from uuid import UUID

from pit.modules.verification.domain.proof import Proof


class ProofRepository(Protocol):
    def add(self, proof: Proof) -> None: ...

    async def get(self, proof_id: UUID) -> Proof | None: ...

    async def list_for_day(self, participation_id: UUID, day: date) -> list[Proof]: ...

    async def phash_used_before(
        self, user_id: UUID, phash: str, exclude_proof_id: UUID
    ) -> bool: ...
