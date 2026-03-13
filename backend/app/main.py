from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# EARLY ENV LOADING (must happen before importing settings / db / routers)
# ---------------------------------------------------------------------------
from app.core.env import load_env_supa

load_env_supa()

# ---------------------------------------------------------------------------
# Regular imports (safe after env is loaded)
# ---------------------------------------------------------------------------
from app.api import api_router
from app.core.config import settings
from app.db import close_db, init_db

from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenant_middleware import TenantMiddleware
from app.core.middleware.audit_context import AuditContextMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
    )

    # -----------------------------------------------------------------------
    # CORS (browser frontend support)
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_BASE_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Middleware order (important)
    # -----------------------------------------------------------------------
    # 1) Request ID (correlation / tracing)
    app.add_middleware(RequestIdMiddleware)

    # 2) Tenant context (sets request.state.tenant_id)
    #    NOTE: auth will later bind tenant from JWT, not header trust
    app.add_middleware(TenantMiddleware)

    # 3) Audit context (reads request_id + tenant/user context)
    app.add_middleware(AuditContextMiddleware)

    # 4) Security headers (late)
    app.add_middleware(SecurityHeadersMiddleware)

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------
    app.include_router(api_router)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    @app.on_event("startup")
    async def on_startup() -> None:
        # Dev convenience only; production should rely on Alembic
        await init_db()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await close_db()

    return app


app = create_app()
