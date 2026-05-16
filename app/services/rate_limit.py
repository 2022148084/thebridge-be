import time
from typing import cast

from fastapi import HTTPException, status
from redis import Redis, RedisError, WatchError

from app.core.config import settings

_GEMINI_RPM_KEY = "rate_limit:gemini:rpm"
_GEMINI_PACING_KEY = "rate_limit:gemini:next_request_ms"
_WINDOW_SECONDS = 60

_redis: Redis | None = None


def _redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _now_ms(client: Redis) -> int:
    seconds, microseconds = cast(tuple[int, int], client.time())
    return seconds * 1000 + microseconds // 1000


def _enforce_gemini_request_pacing(client: Redis) -> None:
    interval_seconds = settings.GEMINI_MIN_REQUEST_INTERVAL_SECONDS
    if interval_seconds <= 0:
        return

    interval_ms = max(1, int(interval_seconds * 1000))

    while True:
        now_ms = _now_ms(client)
        pipe = client.pipeline()
        try:
            pipe.watch(_GEMINI_PACING_KEY)
            current_next = cast(str | None, pipe.get(_GEMINI_PACING_KEY))
            next_request_ms = int(current_next) if current_next is not None else now_ms
            reserved_ms = max(now_ms, next_request_ms)
            new_next_ms = reserved_ms + interval_ms
            ttl_ms = max(_WINDOW_SECONDS * 1000, new_next_ms - now_ms + interval_ms)

            pipe.multi()
            pipe.set(_GEMINI_PACING_KEY, new_next_ms, px=ttl_ms)
            pipe.execute()
            break
        except WatchError:
            continue
        finally:
            pipe.reset()

    delay_ms = reserved_ms - now_ms
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)


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

    try:
        _enforce_gemini_request_pacing(client)
    except RedisError:
        return
