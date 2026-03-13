from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security.deps import get_current_principal


async def get_auth_db(
    request: Request,
    principal: dict = Depends(get_current_principal),
) -> AsyncSession:
    jwt_tenant_id = principal.get("tenant_id")
    if not jwt_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing tenant_id",
        )

    header_tenant_id = getattr(request.state, "header_tenant_id", None)
    if not header_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required tenant header: X-Tenant-Id",
        )

    if str(header_tenant_id) != str(jwt_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant mismatch (header tenant does not match token tenant)",
        )

    # Trusted tenant for the rest of the request
    request.state.tenant_id = str(jwt_tenant_id)

    async for session in get_db(request, tenant_id=str(jwt_tenant_id)):
        yield session
