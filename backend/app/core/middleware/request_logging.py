from __future__ import annotations

import logging
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger("supacrm.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured log line per request with timing and tenant context."""

    async def dispatch(self, request: Request, call_next):
        started = perf_counter()
        response = None
        error = None

        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # pragma: no cover - exercised in live runtime
            error = exc
            raise
        finally:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            state = request.state
            logger.info(
                "request completed",
                extra={
                    "request_id": getattr(state, "request_id", None),
                    "tenant_id": getattr(state, "tenant_id", None) or getattr(state, "header_tenant_id", None),
                    "actor_user_id": getattr(state, "actor_user_id", None),
                    "user_id": getattr(state, "actor_user_id", None) or getattr(state, "user_id", None),
                    "method": request.method,
                    "path": request.url.path,
                    "query": request.url.query or None,
                    "status_code": getattr(response, "status_code", 500),
                    "duration_ms": duration_ms,
                    "client_ip": getattr(state, "actor_ip", None),
                    "outcome": "error" if error else "ok",
                },
            )
