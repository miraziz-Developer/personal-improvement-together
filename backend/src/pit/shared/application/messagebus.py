from __future__ import annotations

import logging
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.application.unit_of_work import UnitOfWork
from pit.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3  # optimistic-locking conflicts are retried with fresh state


@dataclass(frozen=True, kw_only=True)
class Command:
    """An intent to change state. Exactly one handler; its result is returned to the caller."""


type Message = Command | DomainEvent
type CommandHandler = Callable[[Any, UnitOfWork], Awaitable[Any]]
# Event handlers may return follow-up commands (e.g. "challenges, re-check this day").
type EventHandler = Callable[[Any, UnitOfWork], Awaitable[Iterable[Message] | None]]


class MessageBus:
    """Runs a command, then every event (and follow-up command) it causes.

    Each handler gets its own unit of work = its own transaction. Failures in follow-up
    work are logged, not raised, so the caller's already-committed command still succeeds;
    `strict=True` (tests) re-raises them instead.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        command_handlers: Mapping[type[Command], CommandHandler],
        event_handlers: Mapping[type[DomainEvent], Sequence[EventHandler]],
        *,
        strict: bool = False,
    ) -> None:
        self._uow_factory = uow_factory
        self._command_handlers = command_handlers
        self._event_handlers = event_handlers
        self._strict = strict

    async def handle(self, message: Message) -> Any:
        queue: deque[Message] = deque([message])
        result: Any = None
        while queue:
            current = queue.popleft()
            if current is message:
                result = await self._dispatch(current, queue)
                continue
            try:
                await self._dispatch(current, queue)
            except Exception:
                logger.exception("Follow-up message failed: %r", current)
                if self._strict:
                    raise
        return result

    async def _dispatch(self, message: Message, queue: deque[Message]) -> Any:
        if isinstance(message, Command):
            handler = self._command_handlers.get(type(message))
            if handler is None:
                raise LookupError(f"No handler registered for {type(message).__name__}")
            return await self._run(handler, message, queue)
        for event_handler in self._event_handlers.get(type(message), ()):
            follow_ups = await self._run(event_handler, message, queue)
            if follow_ups:
                queue.extend(follow_ups)
        return None

    async def _run(
        self,
        handler: Callable[[Any, UnitOfWork], Awaitable[Any]],
        message: Message,
        queue: deque[Message],
    ) -> Any:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            uow = self._uow_factory()
            try:
                outcome = await handler(message, uow)
            except ConcurrencyConflict:
                if attempt == MAX_ATTEMPTS:
                    raise
                logger.info("Concurrency conflict on %r, retrying (%d)", message, attempt)
                continue
            queue.extend(uow.collect_new_events())
            return outcome
        raise AssertionError("unreachable")
