from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.api_errors import build_error_content
from app.core.config import settings
from app.core.security.jwt import decode_refresh_token
from app.core.security import abuse as security_abuse

logger = logging.getLogger("supacrm.rate_limit")


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


AUTH_RATE_LIMIT_RULES: dict[tuple[str, str], RateLimitRule] = {
    ("POST", "/auth/login"): RateLimitRule(limit=5, window_seconds=60),
    ("POST", "/auth/refresh"): RateLimitRule(limit=10, window_seconds=60),
    ("POST", "/auth/logout"): RateLimitRule(limit=10, window_seconds=60),
    ("POST", "/auth/register"): RateLimitRule(limit=5, window_seconds=60),
}


class SlidingWindowRateLimiter:
    """
    Sliding-window limiter backed by Redis when available.

    Falls back to a local in-memory window when Redis cannot be reached so the
    application can continue to function in constrained test/local environments.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or ""
        self._redis: Redis | None = None
        self._memory_hits: dict[str, deque[float]] = defaultdict(deque)
        self._memory_lock = asyncio.Lock()
        self._redis_disabled = False

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def allow(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        if self._redis_url and not self._redis_disabled:
            try:
                return await self._allow_with_redis(key, limit, window_seconds)
            except Exception:  # pragma: no cover - exercised in live runtime only
                self._redis_disabled = True
                logger.warning("rate limiter fell back to in-memory mode", exc_info=True)

        return await self._allow_in_memory(key, limit, window_seconds)

    async def _allow_with_redis(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        redis = await self._get_redis()
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        member = f"{now_ms}:{asyncio.current_task().get_name() if asyncio.current_task() else 'task'}"

        script = """
        local key = KEYS[1]
        local now_ms = tonumber(ARGV[1])
        local window_ms = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local member = ARGV[4]

        redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
        local count = redis.call('ZCARD', key)
        if count >= limit then
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = math.ceil(window_ms / 1000)
            if oldest[2] then
                local age = now_ms - tonumber(oldest[2])
                retry_after = math.max(1, math.ceil((window_ms - age) / 1000))
            end
            return {0, count, retry_after}
        end

        redis.call('ZADD', key, now_ms, member)
        redis.call('PEXPIRE', key, window_ms + 1000)
        return {1, count + 1, 0}
        """

        allowed, count, retry_after = await redis.eval(script, 1, key, now_ms, window_ms, limit, member)
        remaining = max(0, limit - int(count))
        return RateLimitResult(
            allowed=bool(int(allowed)),
            remaining=remaining,
            retry_after_seconds=int(retry_after),
        )

    async def _allow_in_memory(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._memory_lock:
            hits = self._memory_hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            hits.append(now)
            remaining = max(0, limit - len(hits))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
            )

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: SlidingWindowRateLimiter | None = None):
        super().__init__(app)
        self._limiter = limiter or SlidingWindowRateLimiter(settings.REDIS_URL)

    async def dispatch(self, request: Request, call_next) -> Response:
        rule = AUTH_RATE_LIMIT_RULES.get((request.method.upper(), request.url.path))
        if rule is None:
            return await call_next(request)

        body = await request.body()
        tenant_id = self._extract_tenant_id(request, body)
        client_ip = self._client_ip(request)
        scope_key = self._scope_key(request, tenant_id, client_ip)

        limiter = getattr(getattr(request.app, "state", None), "rate_limiter", None) or self._limiter
        result = await limiter.allow(scope_key, rule.limit, rule.window_seconds)
        if not result.allowed:
            await security_abuse.auth_abuse_tracker.record(
                event_type="auth.rate_limit.exceeded",
                scope_key=scope_key,
                tenant_id=tenant_id,
                ip_address=client_ip,
                path=request.url.path,
                method=request.method,
                limit=rule.limit,
                retry_after_seconds=result.retry_after_seconds,
                severity="warning",
            )
            security_abuse.emit_security_event(
                "auth.rate_limit.exceeded",
                severity="warning",
                request_id=getattr(request.state, "request_id", None),
                tenant_id=tenant_id,
                user_id=getattr(request.state, "actor_user_id", None),
                ip_address=client_ip,
                path=request.url.path,
                method=request.method,
                scope=scope_key,
                limit=rule.limit,
                retry_after_seconds=result.retry_after_seconds,
            )
            response = JSONResponse(
                status_code=429,
                content=build_error_content(
                    code="rate_limited",
                    message="Too many requests. Please retry later.",
                ),
            )
            response.headers["Retry-After"] = str(result.retry_after_seconds)
            return response

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip() or "unknown"
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _extract_tenant_id(self, request: Request, body: bytes) -> str | None:
        header_tenant_id = getattr(request.state, "header_tenant_id", None)
        if header_tenant_id:
            return str(header_tenant_id)

        if not body:
            return None

        payload = self._safe_json(body)
        if not isinstance(payload, dict):
            return None

        if request.url.path == "/auth/login":
            tenant_id = payload.get("tenant_id")
            return str(tenant_id) if tenant_id else None

        refresh_token = payload.get("refresh_token")
        if isinstance(refresh_token, str) and refresh_token.strip():
            try:
                decoded = decode_refresh_token(refresh_token)
            except Exception:
                return None
            tenant_id = decoded.get("tenant_id")
            return str(tenant_id) if tenant_id else None

        return None

    @staticmethod
    def _safe_json(body: bytes) -> Any:
        try:
            return json.loads(body.decode("utf-8") or "{}")
        except Exception:
            return None

    @staticmethod
    def _scope_key(request: Request, tenant_id: str | None, client_ip: str) -> str:
        tenant_scope = tenant_id or "public"
        return f"auth-rate:{request.method.upper()}:{request.url.path}:{tenant_scope}:{client_ip}"
