"""End-to-end business scenarios through the message bus (all modules, in-memory adapters)."""

from datetime import timedelta

import pytest

from pit.modules.challenges.application.commands import CancelParticipation
from pit.modules.challenges.domain.participation import DayStatus, ParticipationStatus
from pit.modules.identity.domain.user import Role
from pit.modules.verification.application.commands import ReviewProof
from pit.modules.verification.application.handlers import DUPLICATE_REASON
from pit.modules.verification.domain.proof import MISSING_CODE_REASON
from pit.modules.verification.domain.verdict import AiDecision, ProofStatus
from pit.modules.wallet.application.commands import Deposit
from pit.modules.wallet.domain.wallet import InsufficientFunds, TransactionKind
from pit.shared.domain.errors import DomainError, InvalidStateTransition
from pit.shared.domain.money import Money
from tests.application.conftest import World

# --- Free mode ----------------------------------------------------------------------------


async def test_free_challenge_completes_and_awards_points(world: World) -> None:
    user = world.add_user()
    challenge = world.add_challenge(duration_days=7, difficulty=2)
    pid = await world.join(user, challenge)

    for _ in range(7):
        await world.prove(user, pid, photo=False)
        await world.next_day()

    participation = world.participation(pid)
    assert participation.status is ParticipationStatus.COMPLETED
    assert participation.days_completed == 7
    # 6 days x 20 + day 7 (streak tier 7+) 24 + completion bonus 100
    assert world.leaderboard.boards["lb:all:global"][user.id] == 6 * 20 + 24 + 100
    assert world.leaderboard.boards[f"lb:all:age:{user.birth_year}"][user.id] == 244


async def test_missed_day_uses_freeze_then_fails(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=14))  # 1 freeze

    await world.next_day()
    participation = world.participation(pid)
    assert participation.days[participation.start_date] is DayStatus.FROZEN
    assert participation.status is ParticipationStatus.ACTIVE

    await world.next_day()
    assert participation.status is ParticipationStatus.FAILED


async def test_proof_counts_for_the_day_it_was_submitted_even_if_ai_answers_after_midnight(
    world: World,
) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=7))
    first_day = world.today

    world.clock.advance(hours=14, minutes=55)  # 23:55 local
    await world.submit(user, pid)
    await world.next_day()  # deadline passes while the proof is still pending
    assert world.participation(pid).days[first_day] is DayStatus.AWAITING_REVIEW

    await world.run_worker()  # AI answers late
    assert world.participation(pid).days[first_day] is DayStatus.DONE


async def test_duplicate_photo_is_rejected(world: World) -> None:
    user = world.add_user()
    pid = await world.join(user, world.add_challenge(duration_days=14))
    await world.prove(user, pid, phash="same-picture")
    await world.next_day()

    proof_id = await world.prove(user, pid, phash="same-picture")

    proof = world.store.proofs[proof_id]
    assert proof.status is ProofStatus.REJECTED
    assert proof.ai_verdict is not None and proof.ai_verdict.reason == DUPLICATE_REASON


# --- Stake mode: money ---------------------------------------------------------------------


async def test_stake_is_frozen_and_fully_returned_on_success(world: World) -> None:
    user = world.add_user()
    challenge = world.add_challenge(duration_days=7)
    await world.deposit(user, 150_000)

    pid = await world.join(user, challenge, stake=100_000)
    wallet = world.wallet(user)
    assert (wallet.available, wallet.locked) == (Money(50_000), Money(100_000))

    for _ in range(7):
        await world.prove(user, pid)
        await world.next_day()

    assert world.participation(pid).status is ParticipationStatus.COMPLETED
    assert (wallet.available, wallet.locked) == (Money(150_000), Money.zero())
    assert [t.kind for t in world.store.ledger] == [
        TransactionKind.DEPOSIT,
        TransactionKind.STAKE_LOCK,
        TransactionKind.STAKE_RELEASE,
    ]


async def test_join_without_enough_money_leaves_no_trace(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 50_000)

    with pytest.raises(InsufficientFunds):
        await world.join(user, world.add_challenge(), stake=100_000)

    assert world.store.participations == {}
    assert world.wallet(user).available == Money(50_000)


async def test_child_can_stake_money_paid_by_parent(world: World) -> None:
    child = world.add_user(adult=False)
    await world.deposit(child, 100_000)

    await world.join(child, world.add_challenge(), stake=50_000)

    assert world.wallet(child).locked == Money(50_000)


async def test_stake_requires_verified_phone(world: World) -> None:
    user = world.add_user(phone=False)
    await world.deposit(user, 100_000)

    with pytest.raises(DomainError, match="telefon"):
        await world.join(user, world.add_challenge(), stake=50_000)


async def test_cancel_before_start_returns_stake(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await world.join(
        user, world.add_challenge(), stake=100_000, start_date=world.today + timedelta(days=1)
    )

    await world.bus.handle(CancelParticipation(user_id=user.id, participation_id=pid))

    assert world.participation(pid).status is ParticipationStatus.CANCELLED
    assert world.wallet(user).available == Money(100_000)
    assert world.wallet(user).locked == Money.zero()


async def test_cannot_cancel_after_start(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(), stake=100_000)

    with pytest.raises(InvalidStateTransition):
        await world.bus.handle(CancelParticipation(user_id=user.id, participation_id=pid))


async def test_webhook_retry_does_not_double_deposit(world: World) -> None:
    user = world.add_user()
    deposit = Deposit(user_id=user.id, amount=70_000, provider_ref="payme-123")

    await world.bus.handle(deposit)
    await world.bus.handle(deposit)

    assert world.wallet(user).available == Money(70_000)


# --- Stake mode: fairness ------------------------------------------------------------------


async def test_ai_rejection_alone_never_takes_the_stake(world: World) -> None:
    user = world.add_user()
    moderator = world.add_user(role=Role.MODERATOR)
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(duration_days=7), stake=100_000)  # 0 freezes
    first_day = world.today

    world.verifier.will_return(
        AiDecision.REJECT, confidence=0.97, reason="Sport zali ko'rinmayapti"
    )
    proof_id = await world.prove(user, pid)
    assert world.store.proofs[proof_id].status is ProofStatus.REJECTED

    await world.next_day()

    # The day is NOT lost: it waits for a human, and the money stays frozen.
    participation = world.participation(pid)
    assert participation.status is ParticipationStatus.ACTIVE
    assert participation.days[first_day] is DayStatus.AWAITING_REVIEW
    assert world.store.proofs[proof_id].status is ProofStatus.NEEDS_REVIEW
    assert world.wallet(user).locked == Money(100_000)

    await world.bus.handle(
        ReviewProof(
            proof_id=proof_id, reviewer_id=moderator.id, approved=False, note="Rasmda zal yo'q"
        )
    )

    assert participation.status is ParticipationStatus.FAILED
    assert world.wallet(user).locked == Money.zero()
    assert world.wallet(user).available == Money.zero()
    assert world.store.ledger[-1].kind is TransactionKind.STAKE_FORFEIT


async def test_moderator_can_overturn_ai_rejection(world: World) -> None:
    user = world.add_user()
    moderator = world.add_user(role=Role.MODERATOR)
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(duration_days=7), stake=100_000)
    first_day = world.today

    world.verifier.will_return(AiDecision.REJECT, confidence=0.97)
    proof_id = await world.prove(user, pid)
    await world.next_day()
    await world.bus.handle(ReviewProof(proof_id=proof_id, reviewer_id=moderator.id, approved=True))

    participation = world.participation(pid)
    assert participation.days[first_day] is DayStatus.DONE
    assert participation.status is ParticipationStatus.ACTIVE
    assert world.wallet(user).locked == Money(100_000)


async def test_doubtful_ai_rejection_goes_to_moderator_immediately(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(), stake=100_000)

    world.verifier.will_return(AiDecision.REJECT, confidence=0.6)
    proof_id = await world.prove(user, pid)

    assert world.store.proofs[proof_id].status is ProofStatus.NEEDS_REVIEW


async def test_photo_without_daily_code_is_not_approved(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(), stake=100_000)

    world.verifier.will_return(AiDecision.APPROVE, confidence=0.99, detected_code="0000")
    proof_id = await world.prove(user, pid)

    proof = world.store.proofs[proof_id]
    assert proof.status is ProofStatus.REJECTED
    assert proof.ai_verdict is not None and proof.ai_verdict.reason == MISSING_CODE_REASON


async def test_user_cannot_review_own_proof(world: World) -> None:
    moderator = world.add_user(role=Role.MODERATOR)
    await world.deposit(moderator, 100_000)
    pid = await world.join(moderator, world.add_challenge(), stake=100_000)
    world.verifier.will_return(AiDecision.REJECT, confidence=0.6)
    proof_id = await world.prove(moderator, pid)

    with pytest.raises(DomainError, match="O'z isbotingiz"):
        await world.bus.handle(
            ReviewProof(proof_id=proof_id, reviewer_id=moderator.id, approved=True)
        )


# --- Paid features switched off (the platform is free for now) ---------------------------


async def test_stake_mode_is_refused_while_paid_features_are_off(world: World) -> None:
    from dataclasses import replace

    from pit.bootstrap import bootstrap
    from pit.modules.challenges.application.commands import JoinChallenge
    from pit.modules.challenges.domain.challenge import ParticipationMode

    free_bus = bootstrap(replace(world.deps, stakes_enabled=False), strict=True)
    user = world.add_user()
    await world.deposit(user, 100_000)
    challenge = world.add_challenge()

    with pytest.raises(DomainError, match="bepul"):
        await free_bus.handle(
            JoinChallenge(
                user_id=user.id,
                challenge_id=challenge.id,
                mode=ParticipationMode.STAKE,
                stake_amount=50_000,
            )
        )
    assert world.wallet(user).locked == Money.zero()

    pid = await free_bus.handle(
        JoinChallenge(user_id=user.id, challenge_id=challenge.id, mode=ParticipationMode.FREE)
    )
    assert world.participation(pid).stake == Money.zero()


async def test_harmful_content_always_goes_to_a_person(world: World) -> None:
    user, moderator = world.add_user(), world.add_user(role=Role.MODERATOR)
    pid = await world.join(user, world.add_challenge())  # free mode: normally AI decides alone
    world.verifier.will_return(AiDecision.APPROVE, confidence=0.99, unsafe=True)
    proof_id = await world.prove(user, pid)

    assert world.store.proofs[proof_id].status is ProofStatus.NEEDS_REVIEW
    assert world.participation(pid).days_completed == 0

    await world.bus.handle(
        ReviewProof(proof_id=proof_id, reviewer_id=moderator.id, approved=False, note="Nomaqbul")
    )
    assert world.store.proofs[proof_id].status is ProofStatus.REJECTED
