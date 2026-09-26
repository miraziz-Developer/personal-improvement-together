from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.challenges.application.commands import RecordTaskApproved, RefreshDay
from pit.modules.challenges.domain.challenge import ProofType
from pit.modules.challenges.domain.events import DayNeedsHumanReview
from pit.modules.challenges.domain.participation import DayEvidence
from pit.modules.challenges.domain.repositories import ChallengeRepository, ParticipationRepository
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.verification.application.commands import ReviewProof, SubmitProof, VerifyProof
from pit.modules.verification.application.day_evidence import task_evidence
from pit.modules.verification.application.ports import (
    ProofVerifier,
    VerificationQueue,
    VerificationRequest,
)
from pit.modules.verification.domain.daily_code import daily_code
from pit.modules.verification.domain.events import ProofApproved, ProofRejected, ProofSubmitted
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.repositories import ProofRepository
from pit.modules.verification.domain.verdict import AiDecision, AiVerdict, ProofStatus
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.application.messagebus import Message
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.errors import DomainError, PermissionDenied

DUPLICATE_REASON = "Bu rasm avval yuborilgan"


class VerificationUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def challenges(self) -> ChallengeRepository: ...

    @property
    def participations(self) -> ParticipationRepository: ...

    @property
    def proofs(self) -> ProofRepository: ...


async def submit_proof(
    cmd: SubmitProof, uow: VerificationUoW, *, clock: Clock, code_secret: bytes
) -> UUID:
    async with uow:
        participation = require(
            await uow.participations.get(cmd.participation_id), "Challenge topilmadi"
        )
        if participation.user_id != cmd.user_id:
            raise PermissionDenied("Bu sizning challenge'ingiz emas")
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        now = clock.now()
        # Proofs always count for the day they were *submitted* in, whatever time the AI answers.
        today = local_date(now, user.timezone)
        participation.ensure_accepts_proof(today, cmd.task_key)

        challenge = require(
            await uow.challenges.get(participation.challenge_id), "Challenge topilmadi"
        )
        proof_type = ProofType.PHOTO if cmd.file_key else ProofType.TEXT
        if not challenge.accepts(proof_type):
            raise DomainError(f"Bu challenge '{proof_type}' turidagi isbotni qabul qilmaydi")

        needs_code = participation.is_stake and cmd.file_key is not None
        proof = Proof.submit(
            proof_id=uuid4(),
            participation_id=participation.id,
            user_id=user.id,
            stake_mode=participation.is_stake,
            for_date=today,
            task_key=cmd.task_key,
            submitted_at=now,
            file_key=cmd.file_key,
            text_note=cmd.text_note,
            phash=cmd.phash,
            expected_code=daily_code(code_secret, participation.id, today) if needs_code else None,
        )
        uow.proofs.add(proof)
        await uow.commit()
        return proof.id


async def verify_proof(cmd: VerifyProof, uow: VerificationUoW, *, verifier: ProofVerifier) -> None:
    async with uow:
        proof = require(await uow.proofs.get(cmd.proof_id), "Isbot topilmadi")
        if proof.status is not ProofStatus.PENDING:
            return  # already decided — the worker may retry a task
        if proof.phash and await uow.proofs.phash_used_before(proof.user_id, proof.phash, proof.id):
            verdict = AiVerdict(
                decision=AiDecision.REJECT,
                confidence=1.0,
                reason=DUPLICATE_REASON,
                model="duplicate-check",
            )
        else:
            participation = require(
                await uow.participations.get(proof.participation_id), "Challenge topilmadi"
            )
            challenge = require(
                await uow.challenges.get(participation.challenge_id), "Challenge topilmadi"
            )
            task = participation.task(proof.for_date, proof.task_key)
            criteria = challenge.verification_prompt
            if task is not None:
                criteria = f"{criteria}\nBugungi vazifa: {task.title} ({task.minutes} daqiqa)"
            verdict = await verifier.verify(
                VerificationRequest(
                    proof_id=proof.id,
                    category=challenge.category,
                    criteria=criteria,
                    file_key=proof.file_key,
                    text_note=proof.text_note,
                    expected_code=proof.expected_code,
                )
            )
        proof.apply_ai_verdict(verdict)
        await uow.commit()


async def review_proof(cmd: ReviewProof, uow: VerificationUoW, *, clock: Clock) -> None:
    async with uow:
        reviewer = require(await uow.users.get(cmd.reviewer_id), "Moderator topilmadi")
        if not reviewer.is_moderator:
            raise PermissionDenied("Faqat moderator isbotni tekshira oladi")
        proof = require(await uow.proofs.get(cmd.proof_id), "Isbot topilmadi")
        if proof.user_id == reviewer.id:
            raise PermissionDenied("O'z isbotingizni tekshira olmaysiz")
        proof.review_by_human(
            reviewer_id=reviewer.id, approved=cmd.approved, note=cmd.note, at=clock.now()
        )
        await uow.commit()


# --- Event handlers ----------------------------------------------------------------------


async def enqueue_verification(
    event: ProofSubmitted, uow: VerificationUoW, *, queue: VerificationQueue
) -> None:
    await queue.enqueue(event.proof_id)


async def task_approved(event: ProofApproved, uow: VerificationUoW) -> list[Message]:
    return [
        RecordTaskApproved(
            participation_id=event.participation_id, day=event.day, task_key=event.task_key
        )
    ]


async def refresh_day_after_rejection(event: ProofRejected, uow: VerificationUoW) -> list[Message]:
    return [RefreshDay(participation_id=event.participation_id, day=event.day)]


async def escalate_for_review(event: DayNeedsHumanReview, uow: VerificationUoW) -> list[Message]:
    """For every required task that only an AI rejected, send its latest proof to a moderator."""
    async with uow:
        participation = require(
            await uow.participations.get(event.participation_id), "Challenge topilmadi"
        )
        proofs = await uow.proofs.list_for_day(event.participation_id, event.day)
        escalated = False
        for key in sorted(participation.required_tasks(event.day)):
            task_proofs = [p for p in proofs if p.task_key == key]
            if task_evidence(task_proofs) is DayEvidence.AI_REJECTED:
                latest = max(
                    (p for p in task_proofs if p.is_ai_rejection), key=lambda p: p.submitted_at
                )
                latest.escalate()
                escalated = True
        if not escalated:
            # Evidence changed in the meantime — let challenges re-judge the day.
            return [RefreshDay(participation_id=event.participation_id, day=event.day)]
        await uow.commit()
        return []
