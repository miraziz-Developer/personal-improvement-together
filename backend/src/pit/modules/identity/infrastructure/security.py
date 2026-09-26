import hmac
import logging
import secrets
import time
from typing import Any
from uuid import UUID

import httpx
from pwdlib import PasswordHash

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._context = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._context.verify(password, password_hash)


class RedisOtpStore:
    """otp:<purpose>:<user_id> -> {phone, code, attempts}; expires after 5 minutes."""

    def __init__(self, redis: Any) -> None:  # redis.asyncio.Redis(decode_responses=True)
        self._redis = redis

    async def put(self, key: str, phone: str, code: str) -> None:
        key = f"otp:{key}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.hset(key, mapping={"phone": phone, "code": code, "attempts": 0})
            pipe.expire(key, OTP_TTL_SECONDS)
            await pipe.execute()

    async def verify(self, key: str, code: str) -> str | None:
        key = f"otp:{key}"
        stored = await self._redis.hgetall(key)
        if not stored:
            return None
        if hmac.compare_digest(stored["code"], code):
            await self._redis.delete(key)
            return str(stored["phone"])
        if await self._redis.hincrby(key, "attempts", 1) >= OTP_MAX_ATTEMPTS:
            await self._redis.delete(key)
        return None


class RedisLinkTokens:
    """tglink:<token> -> user_id for 10 minutes; GETDEL makes every token single-use."""

    TTL_SECONDS = 600

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def issue(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(24)  # [A-Za-z0-9_-], what Telegram allows in /start
        await self._redis.set(f"tglink:{token}", str(user_id), ex=self.TTL_SECONDS)
        return token

    async def consume(self, token: str) -> UUID | None:
        if not token or len(token) > 64:
            return None
        value = await self._redis.getdel(f"tglink:{token}")
        return UUID(value) if value else None


class ConsoleSmsSender:
    """Development only: logs the SMS instead of sending it. Plug an SMS gateway in production."""

    async def send(self, phone: str, text: str) -> None:
        logger.warning("SMS -> %s: %s", phone, text)


class EskizSmsSender:
    """Eskiz.uz SMS gateway. The auth token is cached and renewed when it expires.
    Note: Eskiz requires message templates to be approved in the cabinet first."""

    BASE_URL = "https://notify.eskiz.uz/api"
    TOKEN_TTL_SECONDS = 25 * 24 * 3600  # Eskiz tokens live 30 days

    def __init__(
        self, *, email: str, password: str, sender: str, client: httpx.AsyncClient
    ) -> None:
        self._email = email
        self._password = password
        self._sender = sender
        self._client = client
        self._token: str | None = None
        self._token_expires = 0.0

    async def _auth(self) -> str:
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        response = await self._client.post(
            f"{self.BASE_URL}/auth/login", data={"email": self._email, "password": self._password}
        )
        response.raise_for_status()
        self._token = str(response.json()["data"]["token"])
        self._token_expires = time.monotonic() + self.TOKEN_TTL_SECONDS
        return self._token

    async def send(self, phone: str, text: str) -> None:
        for attempt in (1, 2):
            token = await self._auth()
            response = await self._client.post(
                f"{self.BASE_URL}/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={"mobile_phone": phone.lstrip("+"), "message": text, "from": self._sender},
            )
            if response.status_code == 401 and attempt == 1:
                self._token = None  # token revoked early: log in again once
                continue
            response.raise_for_status()
            return
