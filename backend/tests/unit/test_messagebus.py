from dataclasses import dataclass
from typing import Any

import pytest

from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.application.messagebus import MAX_ATTEMPTS, Command, MessageBus
from tests.fakes import FakeUnitOfWork, InMemoryStore


@dataclass(frozen=True, kw_only=True)
class Ping(Command):
    pass


def bus_with(handler: Any) -> MessageBus:
    store = InMemoryStore()
    return MessageBus(lambda: FakeUnitOfWork(store), {Ping: handler}, {}, strict=True)


async def test_concurrency_conflict_is_retried_with_a_fresh_unit_of_work() -> None:
    seen: list[object] = []

    async def flaky(cmd: Ping, uow: FakeUnitOfWork) -> str:
        seen.append(uow)
        if len(seen) == 1:
            raise ConcurrencyConflict("someone else was faster")
        return "ok"

    assert await bus_with(flaky).handle(Ping()) == "ok"
    assert len(seen) == 2 and seen[0] is not seen[1]


async def test_gives_up_after_max_attempts() -> None:
    calls = 0

    async def always_conflicts(cmd: Ping, uow: FakeUnitOfWork) -> None:
        nonlocal calls
        calls += 1
        raise ConcurrencyConflict("busy")

    with pytest.raises(ConcurrencyConflict):
        await bus_with(always_conflicts).handle(Ping())
    assert calls == MAX_ATTEMPTS
