from typing import cast

from fastapi import HTTPException, status
from redis import Redis, RedisError

from app.core.config import settings

_GEMINI_RPM_KEY = "rate_limit:gemini:rpm"
_WINDOW_SECONDS = 60

_redis: Redis | None = None


def _redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def enforce_gemini_rpm_limit() -> None:
    try:
        client = _redis_client()
        current = cast(int, client.incr(_GEMINI_RPM_KEY))
        ttl = cast(int, client.ttl(_GEMINI_RPM_KEY))
        if current == 1 or ttl == -1:
            client.expire(_GEMINI_RPM_KEY, _WINDOW_SECONDS)
    except RedisError:
        return

    if current > settings.GEMINI_RPM_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini RPM limit exceeded",
        )
