from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

from pit.bootstrap import Dependencies, bootstrap
from pit.modules.challenges.application.commands import CloseDays, JoinChallenge
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.participation import Participation
from pit.modules.identity.domain.user import Role, User
from pit.modules.planning.infrastructure.generators import TemplateLifePlanGenerator
from pit.modules.verification.application.commands import SubmitProof, VerifyProof
from pit.modules.verification.infrastructure.storage import InMemoryStorage
from pit.modules.wallet.application.commands import Deposit
from pit.modules.wallet.domain.wallet import Wallet
from pit.shared.application.clock import local_date
from pit.shared.application.messagebus import MessageBus
from tests.factories import make_challenge
from tests.fakes import (
    FakeClock,
    FakeHasher,
    FakeLeaderboard,
    FakeLinkTokens,
    FakeOtpStore,
    FakePlanGenerator,
    FakePush,
    FakeQueue,
    FakeSms,
    FakeTelegram,
    FakeUnitOfWork,
    FakeVerifier,
    InMemoryStore,
)

TZ = "Asia/Tashkent"
REGION = uuid4()
START = datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo(TZ)).astimezone(UTC)


@dataclass
class World:
    """The whole backend wired with in-memory adapters, plus shortcuts for test scenarios."""

    bus: MessageBus
    store: InMemoryStore
    clock: FakeClock
    verifier: FakeVerifier
    queue: FakeQueue
    leaderboard: FakeLeaderboard
    planner: FakePlanGenerator
    otp: FakeOtpStore
    sms: FakeSms
    deps: Dependencies
    telegram: FakeTelegram
    link_tokens: FakeLinkTokens

    @property
    def today(self) -> date:
        return local_date(self.clock.now(), TZ)

    def add_user(self, *, adult: bool = True, phone: bool = True, role: Role = Role.USER) -> User:
        user = User.register(
            user_id=uuid4(),
            username=f"user_{len(self.store.users)}",
            birth_date=date(1998, 5, 5) if adult else date(2011, 5, 5),
            region_id=REGION,
            today=self.today,
        )
        if phone:
            user.verify_phone("+998901234567")
        user.role = role
        user.pull_events()
        self.store.users[user.id] = user
        return user

    def add_challenge(self, **kwargs: object) -> Challenge:
        challenge = make_challenge(**kwargs)  # type: ignore[arg-type]
        self.store.challenges[challenge.id] = challenge
        return challenge

    async def deposit(self, user: User, amount: int) -> None:
        await self.bus.handle(Deposit(user_id=user.id, amount=amount, provider_ref=str(uuid4())))

    async def join(
        self, user: User, challenge: Challenge, *, stake: int = 0, start_date: date | None = None
    ) -> UUID:
        mode = ParticipationMode.STAKE if stake else ParticipationMode.FREE
        result: UUID = await self.bus.handle(
            JoinChallenge(
                user_id=user.id,
                challenge_id=challenge.id,
                mode=mode,
                stake_amount=stake,
                start_date=start_date,
            )
        )
        return result

    async def submit(
        self,
        user: User,
        participation_id: UUID,
        *,
        task: str = "main",
        photo: bool = True,
        phash: str | None = None,
    ) -> UUID:
        result: UUID = await self.bus.handle(
            SubmitProof(
                user_id=user.id,
                participation_id=participation_id,
                task_key=task,
                file_key="proofs/photo.jpg" if photo else None,
                text_note=None if photo else "Bugun 2 soat kod yozdim",
                phash=phash,
            )
        )
        return result

    async def run_worker(self) -> None:
        while self.queue.pending:
            await self.bus.handle(VerifyProof(proof_id=self.queue.pending.popleft()))

    async def prove(
        self,
        user: User,
        participation_id: UUID,
        *,
        task: str = "main",
        photo: bool = True,
        phash: str | None = None,
    ) -> UUID:
        proof_id = await self.submit(user, participation_id, task=task, photo=photo, phash=phash)
        await self.run_worker()
        return proof_id

    async def next_day(self) -> None:
        """Midnight passes; the daily job closes yesterday for every open participation."""
        self.clock.advance(days=1)
        for participation_id in [p.id for p in self.store.participations.values() if p.is_open]:
            await self.bus.handle(CloseDays(participation_id=participation_id))

    def participation(self, participation_id: UUID) -> Participation:
        return self.store.participations[participation_id]

    def wallet(self, user: User) -> Wallet:
        return self.store.wallets[user.id]


@pytest.fixture
def world() -> World:
    store = InMemoryStore()
    clock = FakeClock(START)
    verifier = FakeVerifier()
    queue = FakeQueue()
    leaderboard = FakeLeaderboard()
    planner = FakePlanGenerator()
    otp_store = FakeOtpStore()
    sms = FakeSms()
    telegram = FakeTelegram()
    link_tokens = FakeLinkTokens()
    deps = Dependencies(
        uow_factory=lambda: FakeUnitOfWork(store),
        clock=clock,
        verifier=verifier,
        verification_queue=queue,
        leaderboard=leaderboard,
        plan_generator=planner,
        life_plan_generator=TemplateLifePlanGenerator(),
        password_hasher=FakeHasher(),
        otp_store=otp_store,
        sms_sender=sms,
        link_tokens=link_tokens,
        daily_code_secret=b"test-secret",
        telegram=telegram,
        web_url="https://pit.uz",
        files=InMemoryStorage(),
        push=FakePush(),
    )
    bus = bootstrap(deps, strict=True)
    return World(
        bus, store, clock, verifier, queue, leaderboard, planner, otp_store, sms, deps,
        telegram, link_tokens,
    )  # fmt: skip
