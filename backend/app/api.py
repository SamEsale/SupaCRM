"""
API router aggregation.

This module exports an APIRouter that main.py mounts on the FastAPI app instance.
"""

from fastapi import APIRouter

from app.audit.routes import router as audit_router
from app.debug.routes import router as debug_router
from app.internal.bootstrap_routes import router as internal_bootstrap_router
from app.tenants.routes import router as tenants_router

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


# Register module routers
api_router.include_router(audit_router)
api_router.include_router(debug_router)
api_router.include_router(internal_bootstrap_router)
api_router.include_router(tenants_router)

# Add other module routers here over time, for example:
from app.auth.routes import router as auth_router

api_router.include_router(auth_router)
