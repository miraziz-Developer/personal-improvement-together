"""Scheduled work, shared by the Celery worker and the local in-process scheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from pit.modules.challenges.application.commands import CloseDays
from pit.modules.coaching.application.commands import SendDailyNudges, SendWeeklySummaries
from pit.modules.verification.domain.verdict import ProofStatus
from pit.modules.verification.infrastructure.tables import proofs

if TYPE_CHECKING:
    from pit.container import Container

logger = logging.getLogger(__name__)
TASHKENT = ZoneInfo("Asia/Tashkent")
DEV_TICK_SECONDS = 600
STALE_PROOF_MINUTES = 3


async def close_all_days(container: Container) -> int:
    """Judge every day that has ended. Idempotent: safe to run as often as you like."""
    async with container.uow_factory() as uow:
        open_ids = await uow.participations.list_open_ids()
    closed = 0
    for participation_id in open_ids:
        try:
            await container.bus.handle(CloseDays(participation_id=participation_id))
            closed += 1
        except Exception:
            logger.exception("Closing days failed for participation %s", participation_id)
    return closed


async def send_nudges(container: Container, kind: Literal["morning", "evening"]) -> int:
    sent: int = await container.bus.handle(SendDailyNudges(kind=kind))
    return sent


async def requeue_stale_proofs(container: Container) -> int:
    """A proof still pending after a few minutes lost its check (restart, crash): ask again.
    Verification is idempotent, so a duplicate is harmless."""
    cutoff = container.clock.now() - timedelta(minutes=STALE_PROOF_MINUTES)
    async with container.uow_factory() as uow:
        rows = await uow.session.execute(
            select(proofs.c.id)
            .where(proofs.c.status == ProofStatus.PENDING.value, proofs.c.submitted_at < cutoff)
            .limit(200)
        )
        stale = list(rows.scalars())
    for proof_id in stale:
        await container.queue.enqueue(proof_id)
    return len(stale)


async def send_weekly_summaries(container: Container) -> int:
    sent: int = await container.bus.handle(SendWeeklySummaries())
    return sent


class DevScheduler:
    """Local stand-in for Celery beat: closes days every 10 minutes and sends the coach's
    morning/evening messages during the 08:00 and 20:00 hours (ids make repeats harmless)."""

    def __init__(self, container: Container) -> None:
        self._container = container
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await requeue_stale_proofs(self._container)
                await close_all_days(self._container)
                hour = datetime.now(TASHKENT).hour
                if hour == 8:
                    await send_nudges(self._container, "morning")
                elif hour == 20:
                    await send_nudges(self._container, "evening")
                elif hour == 21 and datetime.now(TASHKENT).weekday() == 6:
                    await send_weekly_summaries(self._container)
            except Exception:
                logger.exception("Dev scheduler tick failed")
            await asyncio.sleep(DEV_TICK_SECONDS)
