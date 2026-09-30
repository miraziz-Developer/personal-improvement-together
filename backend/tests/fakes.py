"""In-memory adapters for tests. Same ports as production, no I/O."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from uuid import UUID

from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.challenges.domain.group import Group
from pit.modules.challenges.domain.group_message import GroupMessage
from pit.modules.challenges.domain.participation import Participation
from pit.modules.coaching.domain.notification import Notification
from pit.modules.identity.application.ports import GoogleIdentity
from pit.modules.identity.domain.user import User
from pit.modules.moderation.domain.report import Report, ReportStatus
from pit.modules.planning.domain.life_plan import LifePlan
from pit.modules.planning.domain.plan import OnboardingAnswers, Plan, PlanProposal, PlanStatus
from pit.modules.push.application.ports import PushMessage, SubscriptionGone
from pit.modules.push.domain.subscription import PushSubscription
from pit.modules.ranking.domain.scoring import ScoreEntry
from pit.modules.telegram.application.ports import (
    Button,
    ChatUnavailable,
    Keyboard,
    Menu,
    ShareContact,
    TelegramUnavailable,
)
from pit.modules.verification.application.ports import VerificationRequest
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import AiDecision, AiVerdict
from pit.modules.wallet.domain.wallet import LedgerTransaction, Wallet
from pit.shared.application.unit_of_work import UnitOfWork
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError


@dataclass
class InMemoryStore:
    users: dict[UUID, User] = field(default_factory=dict)
    challenges: dict[UUID, Challenge] = field(default_factory=dict)
    participations: dict[UUID, Participation] = field(default_factory=dict)
    groups: dict[UUID, Group] = field(default_factory=dict)
    group_messages: list[GroupMessage] = field(default_factory=list)
    reports: dict[UUID, Report] = field(default_factory=dict)
    push_subscriptions: dict[UUID, PushSubscription] = field(default_factory=dict)
    proofs: dict[UUID, Proof] = field(default_factory=dict)
    wallets: dict[UUID, Wallet] = field(default_factory=dict)
    ledger: list[LedgerTransaction] = field(default_factory=list)
    scores: dict[str, ScoreEntry] = field(default_factory=dict)
    plans: dict[UUID, Plan] = field(default_factory=dict)
    life_plans: dict[UUID, LifePlan] = field(default_factory=dict)
    notifications: dict[UUID, Notification] = field(default_factory=dict)


class _Repo[T: AggregateRoot]:
    """New aggregates are staged until commit, so a failed transaction leaves no trace."""

    def __init__(self, store: dict[UUID, T], seen: set[AggregateRoot]) -> None:
        self._store = store
        self._staged: dict[UUID, T] = {}
        self._seen = seen

    def add(self, item: T) -> None:
        self._staged[item.id] = item
        self._seen.add(item)

    async def get(self, item_id: UUID) -> T | None:
        item = self._staged.get(item_id) or self._store.get(item_id)
        if item is not None:
            self._seen.add(item)
        return item

    def _all(self) -> list[T]:
        items = list({**self._store, **self._staged}.values())
        self._seen.update(items)
        return items

    def flush(self) -> None:
        self._store.update(self._staged)
        self._staged.clear()

    def discard(self) -> None:
        self._staged.clear()


class FakeUsers(_Repo[User]):
    async def get_by_username(self, username: str) -> User | None:
        return next((u for u in self._all() if u.username == username), None)

    async def get_by_telegram_chat(self, chat_id: int) -> User | None:
        return next((u for u in self._all() if u.telegram_chat_id == chat_id), None)

    async def get_by_google_sub(self, sub: str) -> User | None:
        return next((u for u in self._all() if u.google_sub == sub), None)


class FakeChallenges(_Repo[Challenge]):
    pass


class FakeParticipations(_Repo[Participation]):
    async def has_open(self, user_id: UUID, challenge_id: UUID) -> bool:
        return any(
            p.user_id == user_id and p.challenge_id == challenge_id and p.is_open
            for p in self._all()
        )

    async def count_open_stakes(self, user_id: UUID) -> int:
        return sum(1 for p in self._all() if p.user_id == user_id and p.is_open and p.is_stake)

    async def list_in_group(self, group_id: UUID) -> list[UUID]:
        return [p.id for p in self._all() if p.group_id == group_id]

    async def list_open_ids(self, user_id: UUID | None = None) -> list[UUID]:
        return [p.id for p in self._all() if p.is_open and user_id in (None, p.user_id)]


class FakeGroups(_Repo[Group]):
    async def get_by_code(self, invite_code: str) -> Group | None:
        return next((g for g in self._all() if g.invite_code == invite_code), None)


class FakeReports(_Repo[Report]):
    async def has_open(self, reporter_id: UUID, reported_user_id: UUID) -> bool:
        return any(
            r.reporter_id == reporter_id
            and r.reported_user_id == reported_user_id
            and r.status is ReportStatus.OPEN
            for r in self._all()
        )


class FakePushSubscriptions(_Repo[PushSubscription]):
    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        return next((s for s in self._all() if s.endpoint == endpoint), None)

    async def list_for_user(self, user_id: UUID) -> list[PushSubscription]:
        return [s for s in self._all() if s.user_id == user_id]

    async def remove(self, subscription: PushSubscription) -> None:
        self._store.pop(subscription.id, None)
        self._staged.pop(subscription.id, None)


class FakePush:
    """Records pushes; endpoints in `gone` answer like an expired subscription."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushMessage]] = []
        self.gone: set[str] = set()

    async def send(self, subscription: PushSubscription, message: PushMessage) -> None:
        if subscription.endpoint in self.gone:
            raise SubscriptionGone("410")
        self.sent.append((subscription.endpoint, message))


class FakeProofs(_Repo[Proof]):
    async def list_for_user(self, user_id: UUID) -> list[Proof]:
        return [p for p in self._all() if p.user_id == user_id]

    async def list_for_day(self, participation_id: UUID, day: date) -> list[Proof]:
        return [
            p for p in self._all() if p.participation_id == participation_id and p.for_date == day
        ]

    async def phash_used_before(self, user_id: UUID, phash: str, exclude_proof_id: UUID) -> bool:
        return any(
            p.user_id == user_id and p.phash == phash and p.id != exclude_proof_id
            for p in self._all()
        )


class FakeWallets(_Repo[Wallet]):
    pass


class FakePlans(_Repo[Plan]):
    async def delete_for_user(self, user_id: UUID) -> None:
        for plan_id in [p.id for p in self._all() if p.user_id == user_id]:
            self._store.pop(plan_id, None)
            self._staged.pop(plan_id, None)


class FakeLifePlans(_Repo[LifePlan]):
    async def latest_started(self, user_id: UUID) -> LifePlan | None:
        started = [
            p for p in self._all() if p.user_id == user_id and p.status is PlanStatus.STARTED
        ]
        return started[-1] if started else None

    async def delete_for_user(self, user_id: UUID) -> None:
        for plan_id in [p.id for p in self._all() if p.user_id == user_id]:
            self._store.pop(plan_id, None)
            self._staged.pop(plan_id, None)


class FakeNotifications(_Repo[Notification]):
    async def delete_for_user(self, user_id: UUID) -> None:
        for notification_id in [n.id for n in self._all() if n.user_id == user_id]:
            self._store.pop(notification_id, None)
            self._staged.pop(notification_id, None)


class FakeGroupMessages:
    def __init__(self, store: list[GroupMessage]) -> None:
        self._store = store

    async def add(self, message: GroupMessage) -> None:
        self._store.append(message)

    async def recent(self, group_id: UUID, limit: int) -> list[GroupMessage]:
        return [m for m in self._store if m.group_id == group_id][-limit:]

    async def delete_for_user(self, user_id: UUID) -> None:
        self._store[:] = [m for m in self._store if m.user_id != user_id]


class FakeLedger:
    def __init__(self, store: list[LedgerTransaction]) -> None:
        self._store = store
        self._staged: list[LedgerTransaction] = []

    def add(self, transaction: LedgerTransaction) -> None:
        if any(
            t.idempotency_key == transaction.idempotency_key for t in [*self._store, *self._staged]
        ):
            raise AssertionError(f"duplicate idempotency key {transaction.idempotency_key}")
        self._staged.append(transaction)

    async def has(self, idempotency_key: str) -> bool:
        return any(t.idempotency_key == idempotency_key for t in [*self._store, *self._staged])

    def flush(self) -> None:
        self._store.extend(self._staged)
        self._staged.clear()

    def discard(self) -> None:
        self._staged.clear()


class FakeScores:
    def __init__(self, store: dict[str, ScoreEntry]) -> None:
        self._store = store
        self._staged: dict[str, ScoreEntry] = {}

    async def add_if_absent(self, entry: ScoreEntry) -> bool:
        if entry.source_key in self._store or entry.source_key in self._staged:
            return False
        self._staged[entry.source_key] = entry
        return True

    def flush(self) -> None:
        self._store.update(self._staged)
        self._staged.clear()

    def discard(self) -> None:
        self._staged.clear()


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, store: InMemoryStore) -> None:
        super().__init__()
        self._seen: set[AggregateRoot] = set()
        self.users = FakeUsers(store.users, self._seen)
        self.challenges = FakeChallenges(store.challenges, self._seen)
        self.participations = FakeParticipations(store.participations, self._seen)
        self.groups = FakeGroups(store.groups, self._seen)
        self.group_messages = FakeGroupMessages(store.group_messages)
        self.reports = FakeReports(store.reports, self._seen)
        self.push_subscriptions = FakePushSubscriptions(store.push_subscriptions, self._seen)
        self.proofs = FakeProofs(store.proofs, self._seen)
        self.wallets = FakeWallets(store.wallets, self._seen)
        self.ledger = FakeLedger(store.ledger)
        self.scores = FakeScores(store.scores)
        self.plans = FakePlans(store.plans, self._seen)
        self.life_plans = FakeLifePlans(store.life_plans, self._seen)
        self.notifications = FakeNotifications(store.notifications, self._seen)
        self._repos = [
            self.users,
            self.challenges,
            self.participations,
            self.groups,
            self.reports,
            self.push_subscriptions,
            self.proofs,
            self.wallets,
            self.ledger,
            self.scores,
            self.plans,
            self.life_plans,
            self.notifications,
        ]
        self.committed = False

    async def _commit(self) -> None:
        for repo in self._repos:
            repo.flush()
        self.committed = True

    async def rollback(self) -> None:
        for repo in self._repos:
            repo.discard()
        for aggregate in self._seen:
            aggregate.pull_events()  # events of rolled-back work must never be published

    def _seen_aggregates(self) -> Iterable[AggregateRoot]:
        return list(self._seen)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)


class FakeVerifier:
    """Approves honest proofs by default (and 'sees' the expected daily code)."""

    def __init__(self) -> None:
        self.planned: deque[AiVerdict] = deque()
        self.requests: list[VerificationRequest] = []

    def will_return(
        self,
        decision: AiDecision,
        *,
        confidence: float = 0.95,
        reason: str = "test",
        detected_code: str | None = None,
        unsafe: bool = False,
    ) -> None:
        self.planned.append(
            AiVerdict(
                decision=decision,
                confidence=confidence,
                reason=reason,
                model="fake",
                detected_code=detected_code,
                unsafe=unsafe,
            )
        )

    async def verify(self, request: VerificationRequest) -> AiVerdict:
        self.requests.append(request)
        if self.planned:
            return self.planned.popleft()
        return AiVerdict(
            decision=AiDecision.APPROVE,
            confidence=0.95,
            reason="ok",
            model="fake",
            detected_code=request.expected_code,
        )


class FakeQueue:
    def __init__(self) -> None:
        self.pending: deque[UUID] = deque()

    async def enqueue(self, proof_id: UUID) -> None:
        self.pending.append(proof_id)


class FakeLeaderboard:
    def __init__(self) -> None:
        self.boards: dict[str, dict[UUID, int]] = {}

    async def increment(self, keys: list[str], user_id: UUID, points: int) -> None:
        for key in keys:
            board = self.boards.setdefault(key, {})
            board[user_id] = board.get(user_id, 0) + points

    async def remove_user(self, user_id: UUID) -> None:
        for board in self.boards.values():
            board.pop(user_id, None)


class FakePlanGenerator:
    """Returns whatever proposal the test prepared, and remembers what it was asked."""

    def __init__(self) -> None:
        self.next_proposal: PlanProposal | None = None
        self.asked: list[OnboardingAnswers] = []

    async def propose(self, answers: OnboardingAnswers) -> PlanProposal:
        self.asked.append(answers)
        assert self.next_proposal is not None, "test must set next_proposal"
        return self.next_proposal


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeOtpStore:
    def __init__(self) -> None:
        self.codes: dict[str, tuple[str, str]] = {}

    async def put(self, key: str, phone: str, code: str) -> None:
        self.codes[key] = (phone, code)

    async def verify(self, key: str, code: str) -> str | None:
        phone, expected = self.codes.get(key, ("", ""))
        if expected and code == expected:
            del self.codes[key]
            return phone
        return None


class FakeSms:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, phone: str, text: str) -> None:
        self.sent.append((phone, text))


class FakeLinkTokens:
    def __init__(self) -> None:
        self.tokens: dict[str, UUID] = {}

    async def issue(self, user_id: UUID) -> str:
        token = f"token{len(self.tokens) + 1}"
        self.tokens[token] = user_id
        return token

    async def consume(self, token: str) -> UUID | None:
        return self.tokens.pop(token, None)


@dataclass
class SentMessage:
    chat_id: int
    text: str
    keyboard: list[list[Button]]
    menu: list[list[str | ShareContact]] | None = None  # None: unchanged, []: removed

    @property
    def callbacks(self) -> list[str]:
        return [b.callback for row in self.keyboard for b in row if b.callback]

    @property
    def urls(self) -> list[str]:
        return [b.url for row in self.keyboard for b in row if b.url]


class FakeTelegram:
    def __init__(self) -> None:
        self.sent: list[SentMessage] = []
        self.answered: list[str] = []
        self.blocked: set[int] = set()
        self.down = False
        self.files: dict[str, bytes] = {}  # file_id -> content; unknown ids get dummy bytes

    async def send(
        self, chat_id: int, text: str, keyboard: Keyboard = (), *, menu: Menu | None = None
    ) -> None:
        assert not (keyboard and menu is not None), "inline buttons and menu in one message"
        if self.down:
            raise TelegramUnavailable("down")
        if chat_id in self.blocked:
            raise ChatUnavailable("Forbidden: bot was blocked by the user")
        self.sent.append(
            SentMessage(
                chat_id,
                text,
                [list(row) for row in keyboard],
                None if menu is None else [list(row) for row in menu],
            )
        )

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        self.answered.append(callback_id)

    async def download(self, file_id: str) -> bytes:
        return self.files.get(file_id, f"photo:{file_id}".encode())

    def to(self, chat_id: int) -> list[SentMessage]:
        return [m for m in self.sent if m.chat_id == chat_id]

    def last(self, chat_id: int) -> SentMessage:
        return self.to(chat_id)[-1]


class FakeConversation:
    def __init__(self) -> None:
        self.chats: dict[int, dict[str, str]] = {}

    async def get(self, chat_id: int) -> dict[str, str]:
        return dict(self.chats.get(chat_id, {}))

    async def update(self, chat_id: int, **values: str) -> None:
        self.chats.setdefault(chat_id, {}).update(values)

    async def clear(self, chat_id: int) -> None:
        self.chats.pop(chat_id, None)


class FakeProofFiles:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    async def save(self, user_id: UUID, data: bytes) -> tuple[str, str]:
        key = f"proofs/{user_id}/{len(self.saved)}.jpg"
        self.saved[key] = data
        return key, f"phash-{len(self.saved)}"


class FakeGoogle:
    """credential -> identity; anything unknown is an invalid token."""

    def __init__(self) -> None:
        self.accounts: dict[str, GoogleIdentity] = {}

    async def verify(self, credential: str) -> GoogleIdentity:
        if credential not in self.accounts:
            raise DomainError("Google orqali kirish amalga oshmadi. Qayta urinib ko'ring")
        return self.accounts[credential]
