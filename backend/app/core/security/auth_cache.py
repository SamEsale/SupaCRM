from __future__ import annotations

import json
import logging
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
    def __init__(self, redis_url: str | None) -> None:
        self._redis_url = redis_url or ""
        self._redis: Redis | None = None
        self._redis_disabled = False

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def get_principal_snapshot(self, access_token_jti: str) -> dict[str, Any] | None:
        if not self._redis_url or self._redis_disabled:
            return None

        try:
            redis = await self._get_redis()
            raw = await redis.get(principal_cache_key(access_token_jti))
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
            redis = await self._get_redis()
            await redis.set(
                principal_cache_key(access_token_jti),
                self._encode(snapshot),
                ex=max(1, ttl_seconds),
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth principal cache write failed", exc_info=True)

    async def invalidate_principal_snapshot(self, access_token_jti: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            redis = await self._get_redis()
            await redis.delete(principal_cache_key(access_token_jti))
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth principal cache invalidation failed", exc_info=True)

    async def get_profile_snapshot(self, tenant_id: str, user_id: str) -> dict[str, Any] | None:
        if not self._redis_url or self._redis_disabled:
            return None

        try:
            redis = await self._get_redis()
            raw = await redis.get(profile_cache_key(tenant_id, user_id))
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
            redis = await self._get_redis()
            await redis.set(
                profile_cache_key(tenant_id, user_id),
                self._encode(snapshot),
                ex=max(1, ttl_seconds),
            )
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth profile cache write failed", exc_info=True)

    async def invalidate_profile_snapshot(self, tenant_id: str, user_id: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            redis = await self._get_redis()
            await redis.delete(profile_cache_key(tenant_id, user_id))
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth profile cache invalidation failed", exc_info=True)

    async def invalidate_snapshots_for_tenant(self, tenant_id: str) -> None:
        if not self._redis_url or self._redis_disabled:
            return

        try:
            redis = await self._get_redis()
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
        except Exception:  # pragma: no cover - cache failure should not block auth
            self._redis_disabled = True
            logger.warning("auth tenant cache invalidation failed", exc_info=True)

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

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
