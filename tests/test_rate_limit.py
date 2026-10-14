import asyncio
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from ianua.core.rate_limit import (
    RateLimiterExceededError,
    RateLimiterUnavailableError,
    RedisRateLimiter,
)


def test_check_allows_request_under_limit():
    async def scenario():
        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=[1, 60])
        limiter = RedisRateLimiter(redis, key_prefix="ianua-test")

        await limiter.check(
            key="login:192.0.2.1",
            limit=10,
            window_seconds=60,
        )

        assert redis.eval.await_count == 1
        args = redis.eval.await_args.args
        assert args[1:] == (
            1,
            "ianua-test:rate-limit:login:192.0.2.1",
            60,
        )

        """
        redis.eval.assert_awaited_once_with(
            ANY,
            1,
            "ianua-test:rate-limit:login:192.0.2.1",
            60,
        )
        """

    asyncio.run(scenario())


def test_check_reject_request_over_limit():
    async def scenario():
        redis = AsyncMock()
        redis.eval.return_value = [11, 42]
        limiter = RedisRateLimiter(redis)

        with pytest.raises(RateLimiterExceededError) as exc_info:
            await limiter.check(
                key="login:192.0.2.1",
                limit=10,
                window_seconds=60,
            )

        assert exc_info.value.retry_after_seconds == 42

    asyncio.run(scenario())


def test_check_raises_when_redis_is_unavailable():
    async def scenario():
        redis = AsyncMock()
        redis.eval.side_effect = RedisConnectionError("connection failed")
        limiter = RedisRateLimiter(redis)

        with pytest.raises(RateLimiterUnavailableError):
            await limiter.check(
                key="login:192.0.2.1",
                limit=10,
                window_seconds=60,
            )

    asyncio.run(scenario())