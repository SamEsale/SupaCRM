from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.api_errors import build_error_content
from app.core.config import settings
from app.db import set_current_tenant_id, reset_current_tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Option A (recommended):
    - ALWAYS require tenant header for non-public paths (even if Authorization exists).
    - Store the *header* tenant in request.state.header_tenant_id (untrusted).
    - Authenticated DB dependency (get_auth_db) sets request.state.tenant_id from JWT (trusted),
      after verifying it matches the header tenant.
    """

    async def dispatch(self, request: Request, call_next):
        tenant_header = settings.TENANT_HEADER_NAME
        header_tenant_id = request.headers.get(tenant_header)

        # Keep header tenant for diagnostics / mismatch checks
        request.state.header_tenant_id = header_tenant_id

        # Contextvar can hold header tenant (informational); DB should use trusted request.state.tenant_id
        token = set_current_tenant_id(header_tenant_id)

        try:
            if request.method.upper() == "OPTIONS":
                return await call_next(request)

            if settings.REQUIRE_TENANT_HEADER:
                if not self._is_public_path(request.url.path):
                    if not header_tenant_id:
                        return JSONResponse(
                            status_code=400,
                            content=build_error_content(
                                code="bad_request",
                                message=f"Missing required tenant header: {tenant_header}",
                            ),
                        )

            return await call_next(request)

        finally:
            # Reset contextvar to avoid leakage across requests
            try:
                reset_current_tenant_id(token)
            except Exception:
                set_current_tenant_id(None)

    @staticmethod
    def _is_public_path(path: str) -> bool:
        """
        Public paths that do not require tenant context.
        """
        return (
            path == "/favicon.ico"
            or path.startswith("/media")
            or path.startswith("/auth/login")
            or path.startswith("/auth/register")
            or path.startswith("/auth/refresh")
            or path.startswith("/auth/password-reset")
            or path.startswith("/commercial/catalog")
            or path.startswith("/commercial/webhooks")
            or path.startswith("/health")
            or path.startswith("/ready")
            or path.startswith("/docs")
            or path.startswith("/openapi")
            or path.startswith("/redoc")
            or path.startswith("/internal/bootstrap")
        )
