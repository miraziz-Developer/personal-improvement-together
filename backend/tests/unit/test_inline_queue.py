"""The in-process verification queue must never hold a restart hostage."""

import asyncio
from typing import Any
from uuid import uuid4

from pit.container import InlineVerificationQueue


class HangingBus:
    async def handle(self, message: Any) -> None:
        await asyncio.sleep(3600)  # an AI provider that never answers


async def test_drain_gives_up_on_a_hanging_check() -> None:
    queue = InlineVerificationQueue()
    queue.bus = HangingBus()  # type: ignore[assignment]
    await queue.enqueue(uuid4())
    (check,) = queue._running
    await asyncio.wait_for(queue.drain(timeout=0.05), timeout=2)  # returns instead of hanging
    await asyncio.sleep(0.01)  # let the cancellation land
    assert check.cancelled()
