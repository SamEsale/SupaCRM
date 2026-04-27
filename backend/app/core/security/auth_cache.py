from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("supacrm.performance")

PRINCIPAL_CACHE_PREFIX = "supacrm:auth:principal"
PROFILE_CACHE_PREFIX = "supacrm:auth:profile"

# Keep the cache short-lived so it only absorbs repeated requests.
PRINCIPAL_CACHE_MAX_TTL_SECONDS = 60
PROFILE_CACHE_MAX_TTL_SECONDS = 120


def principal_cache_key(access_token_jti: str) -> str:
    return f"{PRINCIPAL_CACHE_PREFIX}:{access_token_jti}"


def profile_cache_key(tenant_id: str, user_id: str) -> str:
    return f"{PROFILE_CACHE_PREFIX}:{tenant_id}:{user_id}"


def ttl_until_expiry(expires_at: datetime, *, maximum_seconds: int) -> int:
    now = datetime.now(timezone.utc)
    remaining = int((expires_at - now).total_seconds())
    return max(1, min(maximum_seconds, remaining))


def ttl_until_epoch(expires_at_epoch: int, *, maximum_seconds: int) -> int:
    now = int(datetime.now(timezone.utc).timestamp())
    remaining = expires_at_epoch - now
    return max(1, min(maximum_seconds, remaining))


class AuthCache:
    def __init__(
        self,
        redis_url: str | None,
        *,
        redis_factory: Callable[..., Redis] | None = None,
    ) -> None:
        self._redis_url = redis_url or ""
        self._redis_disabled = False
        self._redis_factory = redis_factory or Redis.from_url
        self._redis_by_loop: dict[asyncio.AbstractEventLoop, Redis] = {}

    async def aclose(self) -> None:
        cached_clients = list(self._redis_by_loop.items())
        self._redis_by_loop.clear()
        for loop, redis in cached_clients:
            if loop.is_closed():
                continue
            try:
                await redis.aclose()
            except Exception:  # pragma: no cover - shutdown cleanup should stay best-effort
                logger.warning("auth cache redis shutdown failed", exc_info=True)

    async def get_principal_snapshot(self, access_token_jti: str) -> dict[str, Any] | None:
        if not self._redis_url or self._redis_disabled:
            return None

        try:
            raw = await self._run_with_redis(
                lambda redis: redis.get(principal_cache_key(access_token_jti))
            )
            return self._decode(raw)
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth principal cache lookup failed", exc_info=True)
            return None

    async def set_principal_snapshot(
        self,
        access_token_jti: str,
        snapshot: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            await self._run_with_redis(
                lambda redis: redis.set(
                    principal_cache_key(access_token_jti),
                    self._encode(snapshot),
                    ex=max(1, ttl_seconds),
                )
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth principal cache write failed", exc_info=True)

    async def invalidate_principal_snapshot(self, access_token_jti: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            await self._run_with_redis(
                lambda redis: redis.delete(principal_cache_key(access_token_jti))
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth principal cache invalidation failed", exc_info=True)

    async def get_profile_snapshot(self, tenant_id: str, user_id: str) -> dict[str, Any] | None:
        if not self._redis_url or self._redis_disabled:
            return None

        try:
            raw = await self._run_with_redis(
                lambda redis: redis.get(profile_cache_key(tenant_id, user_id))
            )
            return self._decode(raw)
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth profile cache lookup failed", exc_info=True)
            return None

    async def set_profile_snapshot(
        self,
        tenant_id: str,
        user_id: str,
        snapshot: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            await self._run_with_redis(
                lambda redis: redis.set(
                    profile_cache_key(tenant_id, user_id),
                    self._encode(snapshot),
                    ex=max(1, ttl_seconds),
                )
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth profile cache write failed", exc_info=True)

    async def invalidate_profile_snapshot(self, tenant_id: str, user_id: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            await self._run_with_redis(
                lambda redis: redis.delete(profile_cache_key(tenant_id, user_id))
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth profile cache invalidation failed", exc_info=True)

    async def invalidate_snapshots_for_tenant(self, tenant_id: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            await self._run_with_redis(
                lambda redis: self._invalidate_tenant_snapshots(redis, tenant_id)
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth tenant cache invalidation failed", exc_info=True)

    async def _run_with_redis(
        self,
        operation: Callable[[Redis], Awaitable[Any]],
    ) -> Any:
        redis = self._get_redis()
        return await operation(redis)

    def _get_redis(self) -> Redis:
        current_loop = asyncio.get_running_loop()
        redis = self._redis_by_loop.get(current_loop)
        if redis is None:
            redis = self._redis_factory(self._redis_url, decode_responses=True)
            self._redis_by_loop[current_loop] = redis
        return redis

    async def _invalidate_tenant_snapshots(self, redis: Redis, tenant_id: str) -> None:
        principal_keys: list[str] = []
        profile_keys: list[str] = []

        async for key in redis.scan_iter(match=f"{PRINCIPAL_CACHE_PREFIX}:*"):
            raw = await redis.get(key)
            snapshot = self._decode(raw)
            if snapshot and str(snapshot.get("tenant_id")) == str(tenant_id):
                principal_keys.append(str(key))

        async for key in redis.scan_iter(match=f"{PROFILE_CACHE_PREFIX}:{tenant_id}:*"):
            profile_keys.append(str(key))

        if principal_keys:
            await redis.delete(*principal_keys)
        if profile_keys:
            await redis.delete(*profile_keys)

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)

    @staticmethod
    def _decode(raw: str | bytes | None) -> dict[str, Any] | None:
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return None

        data = json.loads(raw)
        return data if isinstance(data, dict) else None


auth_cache = AuthCache(settings.REDIS_URL)
