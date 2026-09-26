from collections.abc import Mapping
from datetime import date
from typing import Any
from uuid import UUID

from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import (
    AiDecision,
    AiVerdict,
    HumanReview,
    ProofStatus,
)
from pit.modules.verification.infrastructure.tables import proofs
from pit.shared.infrastructure.repository import Row, SqlRepository, utc


class SqlProofRepository(SqlRepository[Proof]):
    table = proofs

    def _to_row(self, item: Proof) -> Row:
        verdict, review = item.ai_verdict, item.review
        return {
            "id": item.id,
            "participation_id": item.participation_id,
            "user_id": item.user_id,
            "stake_mode": item.stake_mode,
            "for_date": item.for_date,
            "task_key": item.task_key,
            "submitted_at": utc(item.submitted_at),
            "file_key": item.file_key,
            "text_note": item.text_note,
            "phash": item.phash,
            "expected_code": item.expected_code,
            "status": item.status.value,
            "ai_decision": verdict.decision.value if verdict else None,
            "ai_confidence": verdict.confidence if verdict else None,
            "ai_reason": verdict.reason if verdict else None,
            "ai_model": verdict.model if verdict else None,
            "ai_detected_code": verdict.detected_code if verdict else None,
            "reviewer_id": review.reviewer_id if review else None,
            "review_approved": review.approved if review else None,
            "review_note": review.note if review else None,
            "reviewed_at": utc(review.reviewed_at) if review else None,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Proof:
        verdict = None
        if row["ai_decision"] is not None:
            verdict = AiVerdict(
                decision=AiDecision(row["ai_decision"]),
                confidence=row["ai_confidence"],
                reason=row["ai_reason"],
                model=row["ai_model"],
                detected_code=row["ai_detected_code"],
            )
        review = None
        if row["reviewer_id"] is not None:
            review = HumanReview(
                reviewer_id=row["reviewer_id"],
                approved=row["review_approved"],
                note=row["review_note"],
                reviewed_at=row["reviewed_at"],
            )
        return Proof(
            id=row["id"],
            participation_id=row["participation_id"],
            user_id=row["user_id"],
            stake_mode=row["stake_mode"],
            for_date=row["for_date"],
            task_key=row["task_key"],
            submitted_at=row["submitted_at"],
            file_key=row["file_key"],
            text_note=row["text_note"],
            phash=row["phash"],
            expected_code=row["expected_code"],
            status=ProofStatus(row["status"]),
            ai_verdict=verdict,
            review=review,
        )

    async def list_for_user(self, user_id: UUID) -> list[Proof]:
        stored = await self._select(proofs.c.user_id == user_id)
        return stored + self._pending(lambda p: p.user_id == user_id)

    async def list_for_day(self, participation_id: UUID, day: date) -> list[Proof]:
        stored = await self._select(
            proofs.c.participation_id == participation_id, proofs.c.for_date == day
        )
        pending = self._pending(
            lambda p: p.participation_id == participation_id and p.for_date == day
        )
        return stored + pending

    async def phash_used_before(self, user_id: UUID, phash: str, exclude_proof_id: UUID) -> bool:
        def same_picture(p: Proof) -> bool:
            return p.user_id == user_id and p.phash == phash and p.id != exclude_proof_id

        if self._pending(same_picture):
            return True
        return await self._exists(
            proofs.c.user_id == user_id, proofs.c.phash == phash, proofs.c.id != exclude_proof_id
        )
