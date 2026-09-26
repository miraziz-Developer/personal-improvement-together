from datetime import date
from typing import Protocol
from uuid import UUID

from pit.modules.challenges.domain.participation import DayEvidence
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.repositories import ProofRepository
from pit.modules.verification.domain.verdict import ProofStatus


def task_evidence(proofs: list[Proof]) -> DayEvidence:
    """One task: strongest signal wins — one approved proof is enough; an open one means wait."""
    statuses = {p.status for p in proofs}
    if ProofStatus.APPROVED in statuses:
        return DayEvidence.APPROVED
    if statuses & {ProofStatus.PENDING, ProofStatus.NEEDS_REVIEW}:
        return DayEvidence.PENDING
    if any(p.is_ai_rejection for p in proofs):
        return DayEvidence.AI_REJECTED
    if proofs:
        return DayEvidence.HUMAN_REJECTED
    return DayEvidence.NONE


def day_evidence(proofs: list[Proof], required_tasks: frozenset[str]) -> DayEvidence:
    """A day needs *every* required task. One definitively failed task decides the day
    at once — there is no point in a moderator reviewing the others."""
    per_task = [
        task_evidence([p for p in proofs if p.task_key == key]) for key in sorted(required_tasks)
    ]
    for outcome in (
        DayEvidence.NONE,
        DayEvidence.HUMAN_REJECTED,
        DayEvidence.PENDING,
        DayEvidence.AI_REJECTED,
    ):
        if outcome in per_task:
            return outcome
    return DayEvidence.APPROVED


class _HasProofs(Protocol):
    @property
    def proofs(self) -> ProofRepository: ...


class ProofDayEvidenceReader:
    """Implements the challenges module's DayEvidenceReader port."""

    def __init__(self, uow: _HasProofs) -> None:
        self._uow = uow

    async def evidence_for(
        self, participation_id: UUID, day: date, required_tasks: frozenset[str]
    ) -> DayEvidence:
        proofs = await self._uow.proofs.list_for_day(participation_id, day)
        return day_evidence(proofs, required_tasks)
