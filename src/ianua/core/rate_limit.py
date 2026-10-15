from typing import Literal

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ianua.core.config import settings


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
    def __init__(self, redis: Redis, *, key_prefix: str = "ianua") -> None:
        self._redis = redis
        self._key_prefix = key_prefix

    async def check(self, *, key: str, limit: int, window_seconds: int) -> None:
        redis_key = f"{self._key_prefix}:rate-limit:{key}"

        try:
            result = await self._redis.eval(
                _INCREMENT_SCRIPT,
                1,
                redis_key,
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

RateLimitPolicy = Literal["register", "login", "refresh"]

def rate_limit_dependency(policy: RateLimitPolicy):
    policies = {
        "register": (
            settings.rate_limit_register_requests,
            settings.rate_limit_register_window_seconds,
        ),
        "login": (
            settings.rate_limit_login_requests,
            settings.rate_limit_login_window_seconds,
        ),
        "refresh": (
            settings.rate_limit_refresh_requests,
            settings.rate_limit_refresh_window_seconds,
        ),
    }

    limit, window_seconds = policies[policy]

    async def dependency(request: Request) -> None:
        if not settings.redis_rate_limit_enabled:
            return

        client = request.client
        client_ip = client.host if client is not None else "unknown"

        limiter = RedisRateLimiter(
            request.app.state.redis,
            key_prefix=settings.redis_key_prefix,
        )

        await limiter.check(
            key=f"{policy}:{client_ip}",
            limit=limit,
            window_seconds=window_seconds,
        )

    return dependency