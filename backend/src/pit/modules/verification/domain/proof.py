from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import UUID

from pit.modules.verification.domain.events import (
    ProofApproved,
    ProofRejected,
    ProofSentToReview,
    ProofSubmitted,
)
from pit.modules.verification.domain.policy import codes_match, decide
from pit.modules.verification.domain.verdict import (
    AiDecision,
    AiVerdict,
    HumanReview,
    ProofStatus,
)
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import InvalidStateTransition, InvariantViolation

MAX_NOTE_LENGTH = 2000
MISSING_CODE_REASON = "Rasmda bugungi kod ko'rinmadi"


@dataclass(eq=False, kw_only=True)
class Proof(AggregateRoot):
    participation_id: UUID
    user_id: UUID
    stake_mode: bool
    for_date: date
    task_key: str
    submitted_at: datetime
    file_key: str | None
    text_note: str | None
    phash: str | None
    expected_code: str | None
    status: ProofStatus = ProofStatus.PENDING
    ai_verdict: AiVerdict | None = None
    review: HumanReview | None = None

    @classmethod
    def submit(
        cls,
        *,
        proof_id: UUID,
        participation_id: UUID,
        user_id: UUID,
        stake_mode: bool,
        for_date: date,
        task_key: str,
        submitted_at: datetime,
        file_key: str | None = None,
        text_note: str | None = None,
        phash: str | None = None,
        expected_code: str | None = None,
    ) -> Proof:
        text_note = (text_note or "").strip() or None
        if file_key is None and text_note is None:
            raise InvariantViolation("Isbot uchun rasm yoki matn kerak")
        if text_note is not None and len(text_note) > MAX_NOTE_LENGTH:
            raise InvariantViolation(f"Matn {MAX_NOTE_LENGTH} belgidan oshmasin")
        proof = cls(
            id=proof_id,
            participation_id=participation_id,
            user_id=user_id,
            stake_mode=stake_mode,
            for_date=for_date,
            task_key=task_key,
            submitted_at=submitted_at,
            file_key=file_key,
            text_note=text_note,
            phash=phash,
            expected_code=expected_code,
        )
        proof._record(ProofSubmitted(proof_id=proof_id, participation_id=participation_id))
        return proof

    @property
    def is_ai_rejection(self) -> bool:
        """Rejected by AI and never seen by a human — not final for stake money."""
        return self.status is ProofStatus.REJECTED and self.review is None

    def apply_ai_verdict(self, verdict: AiVerdict) -> None:
        if self.status is not ProofStatus.PENDING:
            raise InvalidStateTransition("Isbot allaqachon tekshirilgan")
        if (
            verdict.decision is AiDecision.APPROVE
            and self.expected_code is not None
            and not codes_match(verdict.detected_code, self.expected_code)
        ):
            verdict = replace(verdict, decision=AiDecision.REJECT, reason=MISSING_CODE_REASON)
        self.ai_verdict = verdict
        self.status = decide(verdict, stake_mode=self.stake_mode)
        self._announce(reason=verdict.reason, by_human=False)

    def escalate(self) -> None:
        """Send an AI rejection to a moderator (a stake day depends on it)."""
        if self.status is ProofStatus.NEEDS_REVIEW:
            return
        if not self.is_ai_rejection:
            raise InvalidStateTransition("Faqat AI rad etgan isbot moderatorga yuboriladi")
        self.status = ProofStatus.NEEDS_REVIEW
        self._announce(reason="", by_human=False)

    def review_by_human(
        self, *, reviewer_id: UUID, approved: bool, note: str, at: datetime
    ) -> None:
        if self.status is not ProofStatus.NEEDS_REVIEW:
            raise InvalidStateTransition("Isbot moderator ko'rigida emas")
        if not approved and not note.strip():
            raise InvariantViolation("Rad etish sababi yozilishi shart")
        self.review = HumanReview(
            reviewer_id=reviewer_id, approved=approved, note=note, reviewed_at=at
        )
        self.status = ProofStatus.APPROVED if approved else ProofStatus.REJECTED
        self._announce(reason=note, by_human=True)

    def _announce(self, *, reason: str, by_human: bool) -> None:
        match self.status:
            case ProofStatus.APPROVED:
                self._record(
                    ProofApproved(
                        proof_id=self.id,
                        participation_id=self.participation_id,
                        user_id=self.user_id,
                        day=self.for_date,
                        task_key=self.task_key,
                        by_human=by_human,
                    )
                )
            case ProofStatus.REJECTED:
                self._record(
                    ProofRejected(
                        proof_id=self.id,
                        participation_id=self.participation_id,
                        user_id=self.user_id,
                        day=self.for_date,
                        task_key=self.task_key,
                        by_human=by_human,
                        reason=reason,
                    )
                )
            case ProofStatus.NEEDS_REVIEW:
                self._record(
                    ProofSentToReview(
                        proof_id=self.id,
                        participation_id=self.participation_id,
                        day=self.for_date,
                        task_key=self.task_key,
                    )
                )
            case ProofStatus.PENDING:
                pass
