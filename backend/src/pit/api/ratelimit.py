"""Fixed-window rate limits in Redis: stops password guessing, SMS flooding and AI cost abuse."""

from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pit.api.deps import ContainerDep
from pit.api.security import read_token
from pit.container import Container

_bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request, container: Container) -> str:
    if container.settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce(container: Container, key: str, limit: int, window_seconds: int) -> None:
    if not container.settings.rate_limits_enabled:
        return
    redis = container.redis
    count = await redis.incr(f"rl:{key}")
    if count == 1:
        await redis.expire(f"rl:{key}", window_seconds)
    if count > limit:
        ttl = await redis.ttl(f"rl:{key}")
        minutes = max(1, (int(ttl) + 59) // 60)
        raise HTTPException(
            429, f"Juda ko'p urinish. {minutes} daqiqadan so'ng qayta urinib ko'ring"
        )


def rate_limit(
    name: str, limit: int, window_seconds: int, *, per: Literal["ip", "user"] = "ip"
) -> Callable[..., Awaitable[None]]:
    async def dependency(
        request: Request,
        container: ContainerDep,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ) -> None:
        subject = client_ip(request, container)
        if per == "user" and credentials is not None:
            # Invalid tokens are rejected by the endpoint itself; until then, limit by IP.
            with suppress(jwt.PyJWTError, ValueError, KeyError):
                subject = str(read_token(credentials.credentials, container.settings))
        await enforce(container, f"{name}:{subject}", limit, window_seconds)

    return dependency
