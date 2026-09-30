from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pit.modules.challenges.infrastructure.repositories import (
    SqlChallengeRepository,
    SqlGroupMessages,
    SqlGroupRepository,
    SqlParticipationRepository,
)
from pit.modules.coaching.infrastructure.repositories import SqlNotificationRepository
from pit.modules.identity.infrastructure.repositories import SqlUserRepository
from pit.modules.moderation.infrastructure.repositories import SqlReportRepository
from pit.modules.planning.infrastructure.repositories import (
    SqlLifePlanRepository,
    SqlPlanRepository,
)
from pit.modules.push.infrastructure.repositories import SqlPushSubscriptionRepository
from pit.modules.ranking.infrastructure.repositories import SqlScoreRepository
from pit.modules.verification.infrastructure.repositories import SqlProofRepository
from pit.modules.wallet.infrastructure.repositories import (
    SqlLedgerRepository,
    SqlWalletRepository,
)
from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.application.unit_of_work import UnitOfWork
from pit.shared.domain.aggregate import AggregateRoot

UNIQUE_VIOLATION = "23505"


class SqlAlchemyUnitOfWork(UnitOfWork):
    """One database transaction. Every module's repository shares the same session."""

    users: SqlUserRepository
    challenges: SqlChallengeRepository
    participations: SqlParticipationRepository
    groups: SqlGroupRepository
    group_messages: SqlGroupMessages
    proofs: SqlProofRepository
    wallets: SqlWalletRepository
    ledger: SqlLedgerRepository
    scores: SqlScoreRepository
    plans: SqlPlanRepository
    life_plans: SqlLifePlanRepository
    notifications: SqlNotificationRepository
    reports: SqlReportRepository
    push_subscriptions: SqlPushSubscriptionRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._session_factory = session_factory
        self._seen: set[AggregateRoot] = set()

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._seen = set()
        self.users = SqlUserRepository(self._session, self._seen)
        self.challenges = SqlChallengeRepository(self._session, self._seen)
        self.participations = SqlParticipationRepository(self._session, self._seen)
        self.groups = SqlGroupRepository(self._session, self._seen)
        self.group_messages = SqlGroupMessages(self._session)
        self.proofs = SqlProofRepository(self._session, self._seen)
        self.wallets = SqlWalletRepository(self._session, self._seen)
        self.plans = SqlPlanRepository(self._session, self._seen)
        self.life_plans = SqlLifePlanRepository(self._session, self._seen)
        self.notifications = SqlNotificationRepository(self._session, self._seen)
        self.reports = SqlReportRepository(self._session, self._seen)
        self.push_subscriptions = SqlPushSubscriptionRepository(self._session, self._seen)
        self.ledger = SqlLedgerRepository(self._session)
        self.scores = SqlScoreRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await super().__aexit__(exc_type, exc, tb)
        await self._session.close()

    async def _commit(self) -> None:
        # Parents before children (users -> challenges -> participations -> proofs ...).
        repositories = (
            self.users,
            self.challenges,
            self.groups,
            self.participations,
            self.proofs,
            self.wallets,
            self.plans,
            self.life_plans,
            self.notifications,
            self.reports,
            self.push_subscriptions,
        )
        try:
            for repository in repositories:
                await repository.save_all()
            await self.ledger.save_all()
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            if getattr(error.orig, "sqlstate", None) == UNIQUE_VIOLATION:
                # e.g. two "join" clicks at once: the retry will see the first one and refuse.
                raise ConcurrencyConflict(str(error.orig)) from error
            raise

    @property
    def session(self) -> AsyncSession:
        """For read-only queries (API views). Writes always go through repositories."""
        return self._session

    async def rollback(self) -> None:
        await self._session.rollback()

    def _seen_aggregates(self) -> Iterable[AggregateRoot]:
        return list(self._seen)
