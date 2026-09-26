from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from pit.modules.verification.domain.daily_code import ALPHABET, CODE_LENGTH, daily_code
from pit.modules.verification.domain.policy import decide
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import AiDecision, AiVerdict, ProofStatus
from pit.shared.domain.errors import InvalidStateTransition, InvariantViolation

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def verdict(decision: AiDecision, confidence: float, code: str | None = None) -> AiVerdict:
    return AiVerdict(
        decision=decision, confidence=confidence, reason="r", model="m", detected_code=code
    )


@pytest.mark.parametrize(
    ("decision", "confidence", "stake", "expected"),
    [
        (AiDecision.APPROVE, 0.5, False, ProofStatus.APPROVED),
        (AiDecision.REJECT, 0.5, False, ProofStatus.REJECTED),
        (AiDecision.APPROVE, 0.85, True, ProofStatus.APPROVED),
        (AiDecision.APPROVE, 0.70, True, ProofStatus.NEEDS_REVIEW),
        (AiDecision.REJECT, 0.95, True, ProofStatus.REJECTED),
        (AiDecision.REJECT, 0.80, True, ProofStatus.NEEDS_REVIEW),
    ],
)
def test_decision_policy(
    decision: AiDecision, confidence: float, stake: bool, expected: ProofStatus
) -> None:
    assert decide(verdict(decision, confidence), stake_mode=stake) is expected


def make_proof(*, stake: bool = True, code: str | None = "AB12") -> Proof:
    return Proof.submit(
        proof_id=uuid4(),
        participation_id=uuid4(),
        user_id=uuid4(),
        stake_mode=stake,
        for_date=date(2026, 10, 1),
        task_key="main",
        submitted_at=NOW,
        file_key="k",
        expected_code=code,
    )


def test_code_matching_is_case_and_space_insensitive() -> None:
    proof = make_proof(code="AB2C")
    proof.apply_ai_verdict(verdict(AiDecision.APPROVE, 0.9, code="ab 2c"))
    assert proof.status is ProofStatus.APPROVED


def test_proof_needs_photo_or_text() -> None:
    with pytest.raises(InvariantViolation):
        Proof.submit(
            proof_id=uuid4(),
            participation_id=uuid4(),
            user_id=uuid4(),
            stake_mode=False,
            for_date=date(2026, 10, 1),
            task_key="main",
            submitted_at=NOW,
            text_note="   ",
        )


def test_verdict_is_applied_once() -> None:
    proof = make_proof(stake=False, code=None)
    proof.apply_ai_verdict(verdict(AiDecision.APPROVE, 0.9))
    with pytest.raises(InvalidStateTransition):
        proof.apply_ai_verdict(verdict(AiDecision.REJECT, 0.9))


def test_human_rejection_requires_a_reason_and_is_final() -> None:
    proof = make_proof(stake=True, code=None)
    proof.apply_ai_verdict(verdict(AiDecision.REJECT, 0.95))
    proof.escalate()
    with pytest.raises(InvariantViolation):
        proof.review_by_human(reviewer_id=uuid4(), approved=False, note="", at=NOW)
    proof.review_by_human(reviewer_id=uuid4(), approved=False, note="Zal ko'rinmayapti", at=NOW)
    assert not proof.is_ai_rejection
    with pytest.raises(InvalidStateTransition):
        proof.escalate()


def test_daily_code_is_deterministic_readable_and_secret_bound() -> None:
    pid = uuid4()
    day = date(2026, 10, 1)
    code = daily_code(b"secret", pid, day)
    assert code == daily_code(b"secret", pid, day)
    assert len(code) == CODE_LENGTH
    assert set(code) <= set(ALPHABET)
    # Different day or different secret gives a different code (collision chance is 1 / 32^4).
    assert code != daily_code(b"secret", pid, date(2026, 10, 2))
    assert code != daily_code(b"another-secret", pid, day)
