"""When is an AI verdict trusted on its own, and when must a human look?

Stake mode is stricter in both directions: the platform keeps failed stakes, so it must
never profit from a doubtful rejection, and never refund on a doubtful approval.
"""

from pit.modules.verification.domain.verdict import AiDecision, AiVerdict, ProofStatus

STAKE_APPROVE_CONFIDENCE = 0.8
STAKE_REJECT_CONFIDENCE = 0.9


def decide(verdict: AiVerdict, *, stake_mode: bool) -> ProofStatus:
    if verdict.unsafe:
        return ProofStatus.NEEDS_REVIEW  # a person looks at it, whatever the mode
    if not stake_mode:
        return (
            ProofStatus.APPROVED if verdict.decision is AiDecision.APPROVE else ProofStatus.REJECTED
        )
    if verdict.decision is AiDecision.APPROVE:
        if verdict.confidence >= STAKE_APPROVE_CONFIDENCE:
            return ProofStatus.APPROVED
        return ProofStatus.NEEDS_REVIEW
    if verdict.confidence >= STAKE_REJECT_CONFIDENCE:
        return ProofStatus.REJECTED
    return ProofStatus.NEEDS_REVIEW


def codes_match(detected: str | None, expected: str) -> bool:
    return detected is not None and detected.replace(" ", "").upper() == expected.upper()
