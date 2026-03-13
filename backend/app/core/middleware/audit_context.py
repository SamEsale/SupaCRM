from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuditContextMiddleware(BaseHTTPMiddleware):
    """
    Captures request context that is useful for audit logging:
    - actor_ip
    - request_id (set by RequestIdMiddleware)
    - actor_user_id (if your auth layer sets request.state.user or similar)

    This does not write audit logs by itself; it just standardizes context fields.
    """

    async def dispatch(self, request: Request, call_next):
        # Best-effort client IP:
        # If behind a trusted proxy, you can rely on X-Forwarded-For as configured in Nginx.
        xff = request.headers.get("X-Forwarded-For")
        request.state.actor_ip = (xff.split(",")[0].strip() if xff else request.client.host)

        # Ensure request_id exists even if RequestIdMiddleware wasn't registered (defensive)
        if not hasattr(request.state, "request_id"):
            request.state.request_id = request.headers.get("X-Request-ID")

        # actor_user_id:
        # If your auth layer sets request.state.user with an "id" field, capture it.
        actor_user_id = None
        user = getattr(request.state, "user", None)
        if user is not None:
            actor_user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)

        request.state.actor_user_id = actor_user_id

        return await call_next(request)
