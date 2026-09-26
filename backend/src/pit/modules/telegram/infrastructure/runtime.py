"""Adapters the bot runs on: Redis chat memory, photo storage, the update gateway and the
local long-polling loop."""

import asyncio
import logging
from contextlib import suppress
from typing import Any
from uuid import UUID, uuid4

from pit.modules.telegram.application.bot import TelegramBot
from pit.modules.telegram.application.ports import (
    ChatUnavailable,
    TelegramApi,
    TelegramUnavailable,
)
from pit.modules.telegram.infrastructure.client import HttpTelegramApi, parse_update
from pit.modules.verification.infrastructure.images import prepare_proof_image
from pit.modules.verification.infrastructure.storage import FileStorage

logger = logging.getLogger(__name__)

CONVERSATION_TTL_SECONDS = 1800
UPDATES_PER_MINUTE = 30  # per chat; far above human pace, stops scripted floods


class RedisConversation:
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def get(self, chat_id: int) -> dict[str, str]:
        return dict(await self._redis.hgetall(f"tg:chat:{chat_id}"))

    async def update(self, chat_id: int, **values: str) -> None:
        key = f"tg:chat:{chat_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=values)
            pipe.expire(key, CONVERSATION_TTL_SECONDS)
            await pipe.execute()

    async def clear(self, chat_id: int) -> None:
        await self._redis.delete(f"tg:chat:{chat_id}")


class StoredProofFiles:
    """Same cleaning as website uploads: metadata stripped, resized, perceptual hash."""

    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    async def save(self, user_id: UUID, data: bytes) -> tuple[str, str]:
        image, phash = await asyncio.to_thread(prepare_proof_image, data)
        key = f"proofs/{user_id}/{uuid4()}.jpg"
        await self._storage.put(key, image, "image/jpeg")
        return key, phash


class TelegramGateway:
    """Where every update enters, from the webhook or the poller: parse, throttle, dispatch.
    Never raises — Telegram would redeliver the same update forever."""

    def __init__(
        self, bot: TelegramBot, api: TelegramApi, redis: Any, *, rate_limits: bool = True
    ) -> None:
        self._bot = bot
        self._api = api
        self._redis = redis
        self._rate_limits = rate_limits

    async def process(self, update: dict[str, Any]) -> None:
        try:
            incoming = parse_update(update)
        except (KeyError, TypeError, ValueError):
            logger.warning("Malformed Telegram update ignored")
            return
        if incoming is None or not await self._allowed(incoming.chat_id):
            return
        try:
            await self._bot.handle(incoming)
        except (ChatUnavailable, TelegramUnavailable):
            logger.warning("Telegram chat %s could not be answered", incoming.chat_id)
        except Exception:
            logger.exception("Telegram update failed")
            with suppress(ChatUnavailable, TelegramUnavailable):
                await self._api.send(
                    incoming.chat_id, "😔 Nimadir xato ketdi. Birozdan so'ng qayta urinib ko'ring."
                )

    async def _allowed(self, chat_id: int) -> bool:
        if not self._rate_limits:
            return True
        key = f"rl:tg:{chat_id}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 60)
        return int(count) <= UPDATES_PER_MINUTE


class TelegramPoller:
    """Local development: pulls updates with getUpdates, so no public webhook URL is needed."""

    def __init__(self, api: HttpTelegramApi, gateway: TelegramGateway) -> None:
        self._api = api
        self._gateway = gateway
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self) -> None:
        try:
            await self._api.configure(webhook_url=None, secret="")
        except (ChatUnavailable, TelegramUnavailable) as error:
            logger.warning("Telegram bot setup failed: %s", error)
        offset = 0
        while True:
            try:
                updates = await self._api.updates(offset)
            except (ChatUnavailable, TelegramUnavailable) as error:
                logger.warning("Telegram polling failed (%s); retrying in 5s", error)
                await asyncio.sleep(5)
                continue
            for update in updates:
                offset = int(update["update_id"]) + 1
                await self._gateway.process(update)
