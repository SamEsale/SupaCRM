"""
API router aggregation.

This module exports an APIRouter that main.py mounts on the FastAPI app instance.
"""

from fastapi import APIRouter, Depends

from app.audit.routes import router as audit_router
from app.auth.routes import router as auth_router
from app.catalog.routes import router as catalog_router
from app.core.security.deps import require_active_tenant
from app.crm.routes import router as crm_router
from app.debug.routes import router as debug_router
from app.internal.bootstrap_routes import router as internal_bootstrap_router
from app.invoicing.routes import router as invoicing_router
from app.quotes.routes import router as quotes_router
from app.reporting.routes import router as reporting_router
from app.sales.routes import router as sales_router
from app.support.routes import router as support_router
from app.tenants.routes import router as tenants_router

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


# Public / non-lifecycle-gated routers
api_router.include_router(auth_router)
api_router.include_router(debug_router)
api_router.include_router(internal_bootstrap_router)

# Protected tenant-facing routers
protected_router = APIRouter(
    dependencies=[Depends(require_active_tenant)]
)

protected_router.include_router(audit_router)
protected_router.include_router(tenants_router)
protected_router.include_router(crm_router)
protected_router.include_router(sales_router)
protected_router.include_router(invoicing_router)
protected_router.include_router(quotes_router)
protected_router.include_router(reporting_router)
protected_router.include_router(support_router)
protected_router.include_router(catalog_router)

api_router.include_router(protected_router)
