"""What the challenges module needs from downstream modules, without depending on them.

Implemented by wallet (StakeEscrow) and verification (DayEvidenceReader), wired in bootstrap.
Both are built from the handler's own unit of work, so they share its transaction.
"""

from datetime import date
from typing import Protocol
from uuid import UUID

from pit.modules.challenges.domain.participation import DayEvidence
from pit.shared.domain.money import Money


class StakeEscrow(Protocol):
    async def lock(self, *, user_id: UUID, participation_id: UUID, stake: Money) -> None: ...


class DayEvidenceReader(Protocol):
    async def evidence_for(
        self, participation_id: UUID, day: date, required_tasks: frozenset[str]
    ) -> DayEvidence: ...
