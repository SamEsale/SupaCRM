from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.integrations.storage.schemas import (
    PresignedUploadRequest,
    PresignedUploadResponse,
    UploadObjectRequest,
    UploadObjectResponse,
)
from app.integrations.storage.service import create_presigned_upload_target, upload_object_bytes
from app.rbac.permissions import PERMISSION_TENANT_ADMIN

router = APIRouter(prefix="/storage", tags=["storage"])


@router.post(
    "/uploads/presign",
    response_model=PresignedUploadResponse,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def create_upload_presign(
    payload: PresignedUploadRequest,
    tenant_id: str = Depends(get_current_tenant_id),
) -> PresignedUploadResponse:
    try:
        target = create_presigned_upload_target(
            purpose=payload.purpose,
            tenant_id=tenant_id,
            file_name=payload.file_name,
            content_type=payload.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PresignedUploadResponse(
        bucket=target.bucket,
        file_key=target.object_key,
        upload_url=target.upload_url,
        download_url=target.download_url,
        expires_in_seconds=target.expires_in_seconds,
    )


@router.post(
    "/uploads",
    response_model=UploadObjectResponse,
    dependencies=[Depends(require_permission(PERMISSION_TENANT_ADMIN))],
)
async def upload_object(
    payload: UploadObjectRequest,
    tenant_id: str = Depends(get_current_tenant_id),
) -> UploadObjectResponse:
    import base64

    try:
        content_type = payload.content_type.strip() or mimetypes.guess_type(payload.file_name)[0] or "application/octet-stream"
        if not content_type.startswith("image/"):
            raise ValueError("Only image uploads are supported")

        file_bytes = base64.b64decode(payload.content_base64.encode("utf-8"), validate=True)
        target = upload_object_bytes(
            purpose=payload.purpose,
            tenant_id=tenant_id,
            file_name=payload.file_name,
            content_type=content_type,
            file_bytes=file_bytes,
        )
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UploadObjectResponse(
        bucket=target.bucket,
        file_key=target.object_key,
        file_url=target.download_url,
    )
