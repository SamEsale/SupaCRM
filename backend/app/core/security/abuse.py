from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

security_logger = logging.getLogger("supacrm.security")


def emit_security_event(
    event_type: str,
    *,
    severity: str = "warning",
    message: str | None = None,
    **fields: Any,
) -> None:
    level = logging.WARNING
    if severity.lower() in {"error", "critical"}:
        level = logging.ERROR
    elif severity.lower() == "info":
        level = logging.INFO

    security_logger.log(
        level,
        message or event_type,
        extra={
            "event_type": event_type,
            "severity": severity,
            **fields,
        },
    )


class AbuseTracker:
    def __init__(
        self,
        redis_url: str | None,
        threshold: int = 3,
        window_seconds: int = 300,
    ) -> None:
        self._redis_url = redis_url or ""
        self._redis: Redis | None = None
        self._redis_disabled = False
        self._memory_lock = asyncio.Lock()
        self._memory_hits: dict[str, deque[float]] = defaultdict(deque)
        self._threshold = threshold
        self._window_seconds = window_seconds

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def record(
        self,
        *,
        event_type: str,
        scope_key: str,
        severity: str = "warning",
        message: str | None = None,
        **fields: Any,
    ) -> int:
        if self._redis_url and not self._redis_disabled:
            try:
                count = await self._increment_with_redis(event_type, scope_key)
            except Exception:  # pragma: no cover - fallback for local/test failures
                self._redis_disabled = True
                count = await self._increment_in_memory(event_type, scope_key)
        else:
            count = await self._increment_in_memory(event_type, scope_key)

        if count >= self._threshold:
            emit_security_event(
                f"{event_type}.suspected",
                severity="error",
                message=message or "Repeated security abuse detected",
                scope=scope_key,
                attempt_count=count,
                threshold=self._threshold,
                **fields,
            )

        return count

    async def _increment_with_redis(self, event_type: str, scope_key: str) -> int:
        redis = await self._get_redis()
        key = self._redis_key(event_type, scope_key)
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, self._window_seconds)
        return count

    async def _increment_in_memory(self, event_type: str, scope_key: str) -> int:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        key = self._redis_key(event_type, scope_key)

        async with self._memory_lock:
            hits = self._memory_hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            hits.append(now)
            return len(hits)

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def _redis_key(event_type: str, scope_key: str) -> str:
        return f"supacrm:abuse:{event_type}:{scope_key}"


auth_abuse_tracker = AbuseTracker(settings.REDIS_URL)
