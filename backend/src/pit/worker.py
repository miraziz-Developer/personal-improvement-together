"""Celery worker + beat (production):

celery -A pit.worker worker --loglevel=info
celery -A pit.worker beat --loglevel=info
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

from pit.celery_app import make_celery
from pit.config import get_settings
from pit.container import Container, build_container
from pit.jobs import close_all_days, send_nudges
from pit.modules.verification.application.commands import VerifyProof
from pit.observability import init_sentry

settings = get_settings().model_copy(update={"inline_tasks": False})
init_sentry(settings, "worker")
app = make_celery(settings)


def _run(work: Callable[[Container], Awaitable[Any]]) -> Any:
    async def main() -> Any:
        container = build_container(settings)
        try:
            return await work(container)
        finally:
            await container.close()

    return asyncio.run(main())


@app.task(name="pit.verify_proof", autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def verify_proof(proof_id: str) -> None:
    _run(lambda c: c.bus.handle(VerifyProof(proof_id=UUID(proof_id))))


@app.task(name="pit.close_days")
def close_days() -> int:
    closed: int = _run(close_all_days)
    return closed


@app.task(name="pit.daily_nudges")
def daily_nudges(kind: Literal["morning", "evening"]) -> int:
    sent: int = _run(lambda c: send_nudges(c, kind))
    return sent
