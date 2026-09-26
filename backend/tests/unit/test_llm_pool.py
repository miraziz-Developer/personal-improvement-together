"""LlmPool: providers take turns and cover for each other."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from pit.shared.infrastructure.llm import COOLDOWN_SECONDS, AiUnavailable, LlmEndpoint, LlmPool


class FakeClient:
    """Answers with a JSON body, or raises, as told; remembers how often it was asked."""

    def __init__(self, *, answer: dict[str, Any] | None = None, raw: str | None = None) -> None:
        self.raw = raw if raw is not None else json.dumps(answer or {"ok": True})
        self.failing: Exception | None = None
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **_: Any) -> Any:
        self.calls += 1
        if self.failing:
            raise self.failing
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.raw))])


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def pool(*clients: FakeClient, clock: Clock | None = None) -> LlmPool:
    endpoints = [LlmEndpoint(f"p{i}", c, f"m{i}") for i, c in enumerate(clients)]
    return LlmPool(endpoints, monotonic=clock or Clock())


async def ask(p: LlmPool) -> str:
    _, label = await p.complete(messages=[], response_format={}, temperature=0, parse=json.loads)
    return label


async def test_providers_take_turns() -> None:
    p = pool(FakeClient(), FakeClient())
    assert [await ask(p) for _ in range(4)] == ["p0/m0", "p1/m1", "p0/m0", "p1/m1"]


async def test_a_failing_provider_hands_over_and_rests() -> None:
    busy, spare = FakeClient(), FakeClient()
    busy.failing = RuntimeError("503 model busy")
    clock = Clock()
    p = pool(busy, spare, clock=clock)

    assert await ask(p) == "p1/m1"  # p0 failed, p1 answered the same request
    assert await ask(p) == "p1/m1"
    assert await ask(p) == "p1/m1"  # p0 is resting: not even asked
    assert busy.calls == 1

    clock.now += COOLDOWN_SECONDS + 1
    busy.failing = None
    assert {await ask(p), await ask(p)} == {"p0/m0", "p1/m1"}  # back in the rotation


async def test_an_unusable_answer_counts_as_a_failure() -> None:
    p = pool(FakeClient(raw="not json"), FakeClient())
    assert await ask(p) == "p1/m1"


async def test_resting_providers_are_still_tried_when_nothing_else_is_left() -> None:
    only = FakeClient()
    only.failing = RuntimeError("429")
    clock = Clock()
    p = pool(only, clock=clock)
    with pytest.raises(AiUnavailable):
        await ask(p)
    only.failing = None
    assert await ask(p) == "p0/m0"  # resting, but better a late answer than none


async def test_everyone_failing_raises_with_the_last_error() -> None:
    first, second = FakeClient(), FakeClient()
    first.failing, second.failing = RuntimeError("429"), TimeoutError()
    with pytest.raises(AiUnavailable) as info:
        await ask(pool(first, second))
    assert isinstance(info.value.__cause__, TimeoutError)
