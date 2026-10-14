from redis.asyncio import Redis
from redis.exceptions import RedisError


class RateLimiterExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Rate limit exceeded")

class RateLimiterUnavailableError(Exception):
    pass


_INCREMENT_SCRIPT = """
    local count = redis.call("INCR", KEYS[1])
    if count == 1 then
        redis.call("EXPIRE", KEYS[1], ARGV[1])
    end
    local ttl = redis.call("TTL", KEYS[1])
    return {count, ttl}
"""

class RedisRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(self, *, key: str, limit: int, window_seconds: int) -> None:
        try:
            result = await self._redis.eval(
                _INCREMENT_SCRIPT,
                1,
                key,
                window_seconds,
            )
        except RedisError as exc:
            raise RateLimiterUnavailableError(
                "Rate limiter storage is unavailable"
            ) from exc

        count, ttl = result

        if count > limit:
            raise RateLimiterExceededError(
                retry_after_seconds=max(1, ttl)
            )