"""Several OpenAI-compatible AI providers used together.

Requests take turns across providers (round robin), which spreads the load over each one's
free-tier limits. When a provider fails — rate limit, "model busy", timeout, unusable answer —
it rests for a minute and the same request goes straight to the next one."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 60.0


class AiUnavailable(Exception):
    """Every provider failed for this request."""


@dataclass(frozen=True, slots=True)
class LlmEndpoint:
    name: str  # "gemini", "groq", ... — shown in logs and stored with each verdict
    client: Any  # openai.AsyncOpenAI or AsyncAzureOpenAI
    model: str

    @property
    def label(self) -> str:
        return f"{self.name}/{self.model}"


class LlmPool:
    def __init__(
        self,
        endpoints: Sequence[LlmEndpoint],
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not endpoints:
            raise ValueError("LlmPool needs at least one endpoint")
        self._endpoints = list(endpoints)
        self._monotonic = monotonic
        self._next = 0
        self._resting_until: dict[str, float] = {}

    @property
    def endpoints(self) -> list[LlmEndpoint]:
        return list(self._endpoints)

    async def complete[T](
        self,
        *,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any],
        temperature: float,
        parse: Callable[[str], T],
        max_tokens: int | None = None,  # long answers (a 90-day roadmap) need room
    ) -> tuple[T, str]:
        """Returns (parsed answer, "provider/model" that gave it). A reply `parse` rejects
        counts as a failure too, so a provider that returns broken JSON is skipped."""
        last_error: Exception | None = None
        for endpoint in self._order():
            try:
                limits = {"max_tokens": max_tokens} if max_tokens else {}
                response = await endpoint.client.chat.completions.create(
                    model=endpoint.model,
                    temperature=temperature,
                    messages=messages,
                    response_format=response_format,
                    **limits,
                )
                return parse(response.choices[0].message.content or ""), endpoint.label
            except Exception as error:
                last_error = error
                self._resting_until[endpoint.name] = self._monotonic() + COOLDOWN_SECONDS
                logger.warning(
                    "AI provider %s failed (%s); trying the next one",
                    endpoint.label,
                    type(error).__name__,
                )
        raise AiUnavailable("All AI providers failed") from last_error

    def _order(self) -> list[LlmEndpoint]:
        count = len(self._endpoints)
        start, self._next = self._next, (self._next + 1) % count
        rotated = [self._endpoints[(start + i) % count] for i in range(count)]
        now = self._monotonic()
        ready = [e for e in rotated if self._resting_until.get(e.name, 0.0) <= now]
        resting = [e for e in rotated if e not in ready]
        # Resting providers are still tried last: better a slow answer than none.
        return ready + resting
