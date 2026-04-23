from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

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
from app.core.api_errors import install_exception_handlers
from app.logging import configure_logging
from app.db import close_db, init_db, run_database_migrations
from app.core.middleware.rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter

from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenant_middleware import TenantMiddleware
from app.core.middleware.audit_context import AuditContextMiddleware
from app.core.middleware.request_logging import RequestLoggingMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.security.abuse import auth_abuse_tracker
from app.integrations.storage.service import LOCAL_UPLOAD_ROOT


configure_logging(settings.LOG_LEVEL)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
    )
    install_exception_handlers(app)
    app.state.rate_limiter = SlidingWindowRateLimiter(settings.REDIS_URL)
    app.state.abuse_tracker = auth_abuse_tracker

    if settings.ENV.lower() != "prod":
        LOCAL_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/media",
            StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)),
            name="media",
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

    # 4) Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 5) Auth rate limiting protects public auth entrypoints.
    app.add_middleware(RateLimitMiddleware)

    # 6) Request logging emits one structured event per request.
    app.add_middleware(RequestLoggingMiddleware)

    # 7) CORS MUST be added last so it wraps the full app and handles
    #    browser preflight OPTIONS requests correctly.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------
    app.include_router(api_router)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    @app.on_event("startup")
    async def on_startup() -> None:
        # Dev convenience only; production should rely on Alembic.
        # Production images set ENV=prod and skip schema creation here.
        if settings.ENV.lower() != "prod":
            await run_database_migrations()
            await init_db()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        rate_limiter = getattr(app.state, "rate_limiter", None)
        if rate_limiter is not None:
            await rate_limiter.aclose()
        abuse_tracker = getattr(app.state, "abuse_tracker", None)
        if abuse_tracker is not None:
            await abuse_tracker.aclose()
        await close_db()

    return app


app = create_app()
