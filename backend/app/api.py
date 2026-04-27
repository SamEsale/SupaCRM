"""
API router aggregation.

This module exports an APIRouter that main.py mounts on the FastAPI app instance.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.readiness import check_database_ready, check_redis_ready, check_storage_ready, storage_readiness_required
from app.core.config import settings

from app.audit.routes import router as audit_router
from app.accounting.routes import router as accounting_router
from app.auth.routes import router as auth_router
from app.catalog.routes import router as catalog_router
from app.commercial.routes import router as commercial_router, webhook_router as commercial_webhook_router
from app.core.security.deps import require_active_tenant
from app.crm.routes import router as crm_router
from app.debug.routes import router as debug_router
from app.expenses.routes import router as expenses_router
from app.finance.routes import router as finance_router
from app.integrations.storage.routes import router as storage_router
from app.internal.commercial_routes import router as internal_commercial_router
from app.internal.bootstrap_routes import router as internal_bootstrap_router
from app.invoicing.routes import router as invoicing_router
from app.marketing.routes import router as marketing_router
from app.payments.routes import router as payments_router
from app.quotes.routes import router as quotes_router
from app.reporting.routes import router as reporting_router
from app.sales.routes import router as sales_router
from app.support.routes import router as support_router
from app.tenants.routes import router as tenants_router

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@api_router.get("/ready", tags=["system"])
async def ready():
    checks: dict[str, str] = {}

    try:
        await check_database_ready()
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - surfaced by route response
        checks["database"] = f"error: {exc}"

    try:
        await check_redis_ready()
        checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover - surfaced by route response
        checks["redis"] = f"error: {exc}"

    if storage_readiness_required():
        try:
            await check_storage_ready()
            checks["storage"] = "ok"
        except Exception as exc:  # pragma: no cover - surfaced by route response
            checks["storage"] = f"error: {exc}"
    else:
        checks["storage"] = "skipped"

    if any(str(value).startswith("error:") for value in checks.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


def attach_feature_routers(router: APIRouter) -> APIRouter:
    # Public / non-lifecycle-gated routers
    router.include_router(auth_router)
    router.include_router(commercial_webhook_router)
    if settings.DEBUG or settings.ENV.lower() != "prod":
        router.include_router(debug_router)
    router.include_router(internal_bootstrap_router)
    router.include_router(internal_commercial_router)
    router.include_router(commercial_router)

    # Protected tenant-facing routers
    protected_router = APIRouter(
        dependencies=[Depends(require_active_tenant)]
    )

    protected_router.include_router(audit_router)
    protected_router.include_router(tenants_router)
    protected_router.include_router(crm_router)
    protected_router.include_router(sales_router)
    protected_router.include_router(accounting_router)
    protected_router.include_router(expenses_router)
    protected_router.include_router(finance_router)
    protected_router.include_router(invoicing_router)
    protected_router.include_router(payments_router)
    protected_router.include_router(quotes_router)
    protected_router.include_router(reporting_router)
    protected_router.include_router(support_router)
    protected_router.include_router(catalog_router)
    protected_router.include_router(storage_router)
    protected_router.include_router(marketing_router)

    router.include_router(protected_router)
    return router


attach_feature_routers(api_router)
