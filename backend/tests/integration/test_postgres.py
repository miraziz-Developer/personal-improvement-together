"""The real persistence layer: mapping, optimistic locking, DB constraints, a full flow."""

from datetime import UTC, date, datetime
from functools import partial
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pit.bootstrap import Dependencies, bootstrap
from pit.modules.challenges.application.commands import CloseDays, JoinChallenge
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.participation import (
    DayStatus,
    Participation,
    ParticipationStatus,
)
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.identity.application import handlers as identity
from pit.modules.identity.application.commands import LinkTelegram
from pit.modules.identity.domain.user import User
from pit.modules.planning.domain.plan import Plan, PlanProposal
from pit.modules.verification.application.commands import SubmitProof, VerifyProof
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import AiDecision, AiVerdict, ProofStatus
from pit.modules.wallet.application.commands import Deposit
from pit.modules.wallet.domain.wallet import Wallet
from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.domain.money import Money
from tests.factories import ANSWERS, make_challenge
from tests.fakes import (
    FakeClock,
    FakeHasher,
    FakeLeaderboard,
    FakeLinkTokens,
    FakeOtpStore,
    FakePlanGenerator,
    FakeQueue,
    FakeSms,
    FakeTelegram,
    FakeVerifier,
)
from tests.integration.conftest import TASHKENT_REGION, UowFactory

TODAY = date(2026, 10, 1)
NOW = datetime(2026, 10, 1, 9, tzinfo=ZoneInfo("Asia/Tashkent")).astimezone(UTC)


async def seed_user(uow_factory: UowFactory, username: str = "ali_2008") -> User:
    user = User.register(
        user_id=uuid4(),
        username=username,
        birth_date=date(2008, 3, 1),
        region_id=TASHKENT_REGION,
        today=TODAY,
    )
    user.verify_phone("+998901234567")
    async with uow_factory() as uow:
        uow.users.add(user)
        await uow.commit()
    return user


async def seed_challenge(uow_factory: UowFactory, **kwargs: object) -> Challenge:
    challenge = make_challenge(**kwargs)  # type: ignore[arg-type]
    async with uow_factory() as uow:
        uow.challenges.add(challenge)
        await uow.commit()
    return challenge


def start(user: User, challenge: Challenge, *, stake: int = 0) -> Participation:
    return Participation.start(
        participation_id=uuid4(),
        user_id=user.id,
        challenge=challenge,
        mode=ParticipationMode.STAKE if stake else ParticipationMode.FREE,
        stake=Money(stake),
        start_date=TODAY,
        today=TODAY,
    )


# --- mapping round trips -----------------------------------------------------------------


async def test_participation_keeps_calendar_and_schedule_history(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    challenge = await seed_challenge(uow_factory, duration_days=14)
    participation = start(user, challenge)
    participation.record_approved_day(TODAY)
    weekends = Schedule.by_weekday({5: [TaskSpec(key="run", title="Yugurish", minutes=40)]})
    participation.change_schedule(weekends, TODAY)
    async with uow_factory() as uow:
        uow.participations.add(participation)
        await uow.commit()

    async with uow_factory() as uow:
        loaded = await uow.participations.get(participation.id)
        loaded_challenge = await uow.challenges.get(challenge.id)

    assert loaded is not None and loaded_challenge is not None
    assert loaded.days == participation.days
    assert loaded.days[TODAY] is DayStatus.DONE
    assert loaded.schedule_history == participation.schedule_history
    assert (loaded.current_streak, loaded.freezes_total) == (1, participation.freezes_total)
    assert loaded_challenge.default_schedule == challenge.default_schedule
    assert loaded_challenge.proof_types == challenge.proof_types
    assert loaded_challenge.stake_policy == challenge.stake_policy


async def test_proof_keeps_verdict_and_review(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    moderator = await seed_user(uow_factory, "moderator")
    participation = start(user, await seed_challenge(uow_factory), stake=50_000)
    proof = Proof.submit(
        proof_id=uuid4(),
        participation_id=participation.id,
        user_id=user.id,
        stake_mode=True,
        for_date=TODAY,
        task_key="main",
        submitted_at=NOW,
        file_key="proofs/a.jpg",
        phash="abc",
        expected_code="K7X2",
    )
    proof.apply_ai_verdict(
        AiVerdict(decision=AiDecision.REJECT, confidence=0.6, reason="Zal ko'rinmaydi", model="m")
    )
    proof.review_by_human(reviewer_id=moderator.id, approved=True, note="Zal bor", at=NOW)
    async with uow_factory() as uow:
        uow.participations.add(participation)
        uow.proofs.add(proof)
        await uow.commit()

    async with uow_factory() as uow:
        loaded = await uow.proofs.get(proof.id)
        same_picture = await uow.proofs.phash_used_before(user.id, "abc", uuid4())

    assert loaded is not None
    assert loaded.status is ProofStatus.APPROVED
    assert loaded.ai_verdict == proof.ai_verdict
    assert loaded.review == proof.review
    assert loaded.submitted_at == NOW
    assert same_picture


async def test_plan_keeps_answers_and_proposal(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    plan = Plan.draft(
        plan_id=uuid4(),
        user_id=user.id,
        answers=ANSWERS,
        proposal=PlanProposal(
            title="Backend",
            description="FastAPI",
            category=make_challenge().category,
            duration_days=30,
            difficulty=3,
            verification_prompt="Kod ko'rinsin",
            schedule=Schedule.by_weekday({0: [TaskSpec(key="lesson", title="Dars", minutes=60)]}),
        ),
    )
    async with uow_factory() as uow:
        uow.plans.add(plan)
        await uow.commit()

    async with uow_factory() as uow:
        loaded = await uow.plans.get(plan.id)

    assert loaded is not None
    assert (loaded.answers, loaded.proposal) == (plan.answers, plan.proposal)


# --- concurrency and constraints ---------------------------------------------------------


async def test_concurrent_wallet_changes_are_detected(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    async with uow_factory() as uow:
        uow.wallets.add(Wallet.open(user.id))
        await uow.commit()

    async with uow_factory() as first, uow_factory() as second:
        wallet_a = await first.wallets.get(user.id)
        wallet_b = await second.wallets.get(user.id)
        assert wallet_a is not None and wallet_b is not None
        first.ledger.add(wallet_a.deposit(Money(10_000), idempotency_key="a", at=NOW))
        second.ledger.add(wallet_b.deposit(Money(20_000), idempotency_key="b", at=NOW))
        await first.commit()
        with pytest.raises(ConcurrencyConflict):
            await second.commit()

    async with uow_factory() as uow:
        wallet = await uow.wallets.get(user.id)
    assert wallet is not None and wallet.available == Money(10_000)


async def test_readers_do_not_conflict_with_writers(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    participation = start(user, await seed_challenge(uow_factory))
    async with uow_factory() as uow:
        uow.participations.add(participation)
        await uow.commit()

    async with uow_factory() as reader, uow_factory() as writer:
        assert await reader.participations.get(participation.id) is not None
        written = await writer.participations.get(participation.id)
        assert written is not None
        written.record_approved_day(TODAY)
        await writer.commit()
        await reader.commit()  # read-only: nothing to write, so no conflict


async def test_database_allows_only_one_open_run_per_challenge(uow_factory: UowFactory) -> None:
    user = await seed_user(uow_factory)
    challenge = await seed_challenge(uow_factory)

    async with uow_factory() as first, uow_factory() as second:
        first.participations.add(start(user, challenge))
        second.participations.add(start(user, challenge))  # e.g. a double click
        await first.commit()
        with pytest.raises(ConcurrencyConflict):
            await second.commit()


# --- a whole stake challenge on Postgres ---------------------------------------------------


async def test_stake_challenge_end_to_end(
    uow_factory: UowFactory, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await seed_user(uow_factory)
    challenge = await seed_challenge(uow_factory, duration_days=7)
    clock, queue = FakeClock(NOW), FakeQueue()
    otp_store, sms = FakeOtpStore(), FakeSms()
    bus = bootstrap(
        Dependencies(
            uow_factory=uow_factory,
            clock=clock,
            verifier=FakeVerifier(),
            verification_queue=queue,
            leaderboard=FakeLeaderboard(),
            plan_generator=FakePlanGenerator(),
            password_hasher=FakeHasher(),
            otp_store=otp_store,
            sms_sender=sms,
            link_tokens=FakeLinkTokens(),
            daily_code_secret=b"test-secret",
            telegram=FakeTelegram(),
        ),
        strict=True,
    )

    await bus.handle(Deposit(user_id=user.id, amount=150_000, provider_ref="payme-1"))
    pid = await bus.handle(
        JoinChallenge(
            user_id=user.id,
            challenge_id=challenge.id,
            mode=ParticipationMode.STAKE,
            stake_amount=100_000,
        )
    )
    for _ in range(7):
        await bus.handle(SubmitProof(user_id=user.id, participation_id=pid, file_key="p.jpg"))
        while queue.pending:
            await bus.handle(VerifyProof(proof_id=queue.pending.popleft()))
        clock.advance(days=1)
        async with uow_factory() as uow:
            open_ids = await uow.participations.list_open_ids()
        for open_id in open_ids:
            await bus.handle(CloseDays(participation_id=open_id))

    async with uow_factory() as uow:
        participation = await uow.participations.get(pid)
        wallet = await uow.wallets.get(user.id)
    assert participation is not None and participation.status is ParticipationStatus.COMPLETED
    assert wallet is not None
    assert (wallet.available, wallet.locked) == (Money(150_000), Money.zero())

    async with session_factory() as session:
        kinds = await session.execute(
            text("SELECT kind FROM ledger_transactions ORDER BY created_at, kind")
        )
        unbalanced = await session.execute(
            text("SELECT transaction_id FROM ledger_postings GROUP BY 1 HAVING SUM(amount) <> 0")
        )
        points = await session.execute(
            text("SELECT SUM(points) FROM score_entries WHERE user_id = :u"), {"u": user.id}
        )
        assert list(kinds.scalars()) == ["deposit", "stake_lock", "stake_release"]
        assert unbalanced.first() is None  # double-entry: every transaction sums to zero
        assert points.scalar_one() > 0


# --- telegram link -------------------------------------------------------------------------


async def test_telegram_chat_belongs_to_one_account(uow_factory: UowFactory) -> None:
    first = await seed_user(uow_factory, "birinchi")
    second = await seed_user(uow_factory, "ikkinchi")
    tokens = FakeLinkTokens()
    handler = partial(identity.link_telegram, tokens=tokens)

    await handler(
        LinkTelegram(token=await tokens.issue(first.id), chat_id=9_000_000_001), uow_factory()
    )
    await handler(
        LinkTelegram(token=await tokens.issue(second.id), chat_id=9_000_000_001), uow_factory()
    )

    async with uow_factory() as uow:
        owner = await uow.users.get_by_telegram_chat(9_000_000_001)
        assert owner is not None and owner.id == second.id
        reloaded = await uow.users.get(first.id)
        assert reloaded is not None and reloaded.telegram_chat_id is None
