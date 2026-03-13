from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db_admin import get_admin_session

router = APIRouter(prefix="/internal/bootstrap", tags=["internal-bootstrap"])


def require_bootstrap_key(x_bootstrap_key: str | None = Header(default=None)) -> None:
    if not x_bootstrap_key or x_bootstrap_key != settings.BOOTSTRAP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bootstrap key",
        )


@router.get("/ping", dependencies=[Depends(require_bootstrap_key)])
async def ping() -> dict:
    return {"ok": True}


@router.get("/db", dependencies=[Depends(require_bootstrap_key)])
async def db_check(admin_session: AsyncSession = Depends(get_admin_session)) -> dict:
    result = await admin_session.execute(text("select 1"))
    return {"db": result.scalar_one()}
