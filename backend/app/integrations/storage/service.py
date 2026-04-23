from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Literal

from minio import Minio

from app.core.config import settings

UploadPurpose = Literal["product-image", "tenant-logo"]

OBJECT_PURPOSE_PREFIXES: dict[UploadPurpose, str] = {
    "product-image": "product-images",
    "tenant-logo": "tenant-logos",
}

logger = logging.getLogger(__name__)

# Local development fallback storage. Production continues to use MinIO only.
LOCAL_UPLOAD_ROOT = Path(__file__).resolve().parents[4] / ".local-storage" / "uploads"


@dataclass(slots=True)
class PresignedUploadTarget:
    bucket: str
    object_key: str
    upload_url: str
    download_url: str
    expires_in_seconds: int


@dataclass(slots=True)
class StoredObjectResult:
    bucket: str
    object_key: str
    download_url: str


def _is_production() -> bool:
    return settings.ENV.strip().lower() == "prod"


def _local_media_url(object_key: str) -> str:
    base_url = settings.APP_BASE_URL.strip().rstrip("/") or "http://localhost:8000"
    parsed_base = urlsplit(base_url)
    if parsed_base.scheme in {"http", "https"} and parsed_base.hostname == "localhost":
        normalized_netloc = parsed_base.netloc.replace("localhost", "127.0.0.1", 1)
        base_url = urlunsplit(
            (
                parsed_base.scheme,
                normalized_netloc,
                parsed_base.path,
                parsed_base.query,
                parsed_base.fragment,
            )
        ).rstrip("/")
    return f"{base_url}/media/{object_key}"


def _local_object_path(object_key: str) -> Path:
    return LOCAL_UPLOAD_ROOT / object_key


def _store_locally(object_key: str, file_bytes: bytes) -> None:
    path = _local_object_path(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)


def _fallback_presigned_upload_target(
    *,
    object_key: str,
    expires_in_seconds: int,
) -> PresignedUploadTarget:
    download_url = _local_media_url(object_key)
    return PresignedUploadTarget(
        bucket=settings.MINIO_BUCKET,
        object_key=object_key,
        upload_url=download_url,
        download_url=download_url,
        expires_in_seconds=expires_in_seconds,
    )


def _get_client() -> Minio:
    endpoint = settings.MINIO_ENDPOINT.strip()
    if not endpoint:
        raise ValueError("MINIO_ENDPOINT is not configured")

    access_key = (settings.MINIO_ACCESS_KEY or settings.MINIO_ROOT_USER).strip()
    secret_key = (settings.MINIO_SECRET_KEY or settings.MINIO_ROOT_PASSWORD).strip()
    if not access_key or not secret_key:
        raise ValueError("MinIO credentials are not configured")

    normalized_endpoint = endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        normalized_endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=bool(settings.MINIO_USE_SSL or endpoint.startswith("https://")),
    )


def _ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def _sanitize_filename(file_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", file_name.strip())
    cleaned = cleaned.strip("-._")
    return cleaned or "upload"


def build_object_key(*, purpose: UploadPurpose, tenant_id: str, file_name: str) -> str:
    prefix = OBJECT_PURPOSE_PREFIXES[purpose]
    safe_name = _sanitize_filename(file_name)
    token = uuid.uuid4().hex
    return f"{prefix}/{tenant_id}/{token}-{safe_name}"


def create_presigned_upload_target(
    *,
    purpose: UploadPurpose,
    tenant_id: str,
    file_name: str,
    content_type: str,
    expires_in_seconds: int = 900,
) -> PresignedUploadTarget:
    object_key = build_object_key(
        purpose=purpose,
        tenant_id=tenant_id,
        file_name=file_name,
    )

    _ = content_type

    try:
        client = _get_client()
        _ensure_bucket_exists(client, settings.MINIO_BUCKET)
        upload_url = client.presigned_put_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=expires_in_seconds),
        )
        download_url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=expires_in_seconds),
        )
        return PresignedUploadTarget(
            bucket=settings.MINIO_BUCKET,
            object_key=object_key,
            upload_url=upload_url,
            download_url=download_url,
            expires_in_seconds=expires_in_seconds,
        )
    except Exception as exc:
        if _is_production():
            raise
        logger.warning("Falling back to local media storage for presigned upload target", exc_info=True)
        return _fallback_presigned_upload_target(
            object_key=object_key,
            expires_in_seconds=expires_in_seconds,
        )


def upload_object_bytes(
    *,
    purpose: UploadPurpose,
    tenant_id: str,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
) -> StoredObjectResult:
    object_key = build_object_key(
        purpose=purpose,
        tenant_id=tenant_id,
        file_name=file_name,
    )
    try:
        client = _get_client()
        _ensure_bucket_exists(client, settings.MINIO_BUCKET)

        stream = BytesIO(file_bytes)
        client.put_object(
            settings.MINIO_BUCKET,
            object_key,
            stream,
            length=len(file_bytes),
            content_type=content_type or "application/octet-stream",
        )
        if not _is_production():
            # Local development keeps browser previews on the backend origin so
            # uploaded media renders without depending on an internal MinIO URL.
            _store_locally(object_key, file_bytes)
            return StoredObjectResult(
                bucket=settings.MINIO_BUCKET,
                object_key=object_key,
                download_url=_local_media_url(object_key),
            )

        download_url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=3600),
        )

        return StoredObjectResult(
            bucket=settings.MINIO_BUCKET,
            object_key=object_key,
            download_url=download_url,
        )
    except Exception as exc:
        if _is_production():
            raise
        logger.warning("Falling back to local media storage for upload", exc_info=True)
        _store_locally(object_key, file_bytes)
        return StoredObjectResult(
            bucket=settings.MINIO_BUCKET,
            object_key=object_key,
            download_url=_local_media_url(object_key),
        )


def presign_download_url(object_key: str, *, expires_in_seconds: int = 3600) -> str:
    if not _is_production():
        local_path = _local_object_path(object_key)
        if local_path.exists():
            return _local_media_url(object_key)

    try:
        client = _get_client()
        _ensure_bucket_exists(client, settings.MINIO_BUCKET)
        return client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=expires_in_seconds),
        )
    except Exception as exc:
        if _is_production():
            raise
        logger.warning("Falling back to local media storage for download URL", exc_info=True)
        return _local_media_url(object_key)
