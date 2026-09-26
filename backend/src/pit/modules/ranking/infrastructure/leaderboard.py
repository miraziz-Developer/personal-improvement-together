from typing import Any
from uuid import UUID

# Weekly and seasonal boards are only interesting for a while; all-time boards live forever.
PERIOD_TTL_SECONDS = 120 * 24 * 3600


class RedisLeaderboard:
    """Redis sorted sets: one per (period, scope). A projection of `score_entries`."""

    def __init__(self, redis: Any) -> None:  # redis.asyncio.Redis(decode_responses=True)
        self._redis = redis

    async def increment(self, keys: list[str], user_id: UUID, points: int) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            for key in keys:
                pipe.zincrby(key, points, str(user_id))
                if not key.startswith("lb:all:"):
                    pipe.expire(key, PERIOD_TTL_SECONDS)
            await pipe.execute()

    async def remove_user(self, user_id: UUID) -> None:
        async for key in self._redis.scan_iter(match="lb:*", count=500):
            await self._redis.zrem(key, str(user_id))

    async def top(self, key: str, *, limit: int, offset: int = 0) -> list[tuple[UUID, int]]:
        rows = await self._redis.zrevrange(key, offset, offset + limit - 1, withscores=True)
        return [(UUID(member), int(score)) for member, score in rows]

    async def position(self, key: str, user_id: UUID) -> tuple[int, int] | None:
        rank = await self._redis.zrevrank(key, str(user_id))
        if rank is None:
            return None
        score = await self._redis.zscore(key, str(user_id))
        return int(rank) + 1, int(score or 0)

    async def size(self, key: str) -> int:
        return int(await self._redis.zcard(key))
