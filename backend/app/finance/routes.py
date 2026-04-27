from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.finance.services.invoice_pdf_service import build_invoice_pdf
from app.rbac.permissions import PERMISSION_BILLING_ACCESS

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get(
    "/invoices/{invoice_id}/pdf",
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def download_invoice_pdf(
    invoice_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> StreamingResponse:
    pdf_bytes = await build_invoice_pdf(
        db,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )
    if pdf_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    response = StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="invoice-{invoice_id}.pdf"'
    return response
