from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import db as app_db
from app.integrations.storage import routes as storage_routes
from app.integrations.storage import service as storage_service
from app.integrations.storage.schemas import UploadObjectRequest
import app.main as app_main
from app.main import create_app
from app.marketing import routes as marketing_routes
from app.marketing.service import (
    MarketingIntegrationsDetails,
    SmtpSettingsDetails,
    WhatsAppIntegrationDetails,
)
from app.tenants import routes as tenant_routes
from app.tenants.schemas import TenantBrandingUpdateRequest
from app.tenants.service import TenantBrandingDetails


def test_tenant_branding_migration_points_to_the_commercial_core_revision() -> None:
    from importlib import util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "20260406_02_add_tenant_branding_and_integrations.py"
    )
    spec = util.spec_from_file_location("tenant_branding_migration", migration_path)
    assert spec is not None and spec.loader is not None

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "20260406_02"
    assert module.down_revision == "20260406_01"


@pytest.mark.asyncio
async def test_upload_object_route_decodes_base64_and_returns_file_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_upload_object_bytes(
        *,
        purpose: str,
        tenant_id: str,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
    ) -> SimpleNamespace:
        captured.update(
            purpose=purpose,
            tenant_id=tenant_id,
            file_name=file_name,
            content_type=content_type,
            file_bytes=file_bytes,
        )
        return SimpleNamespace(
            bucket="supacrm",
            object_key="tenant-logos/tenant-1/logo.png",
            download_url="https://cdn.example.com/logo.png",
        )

    monkeypatch.setattr(
        storage_routes, "upload_object_bytes", _fake_upload_object_bytes
    )

    payload = UploadObjectRequest(
        purpose="tenant-logo",
        file_name="logo.png",
        content_type="image/png",
        content_base64=base64.b64encode(b"logo-bytes").decode("ascii"),
    )
    response = await storage_routes.upload_object(payload, tenant_id="tenant-1")

    assert captured == {
        "purpose": "tenant-logo",
        "tenant_id": "tenant-1",
        "file_name": "logo.png",
        "content_type": "image/png",
        "file_bytes": b"logo-bytes",
    }
    assert response.bucket == "supacrm"
    assert response.file_key == "tenant-logos/tenant-1/logo.png"
    assert response.file_url == "https://cdn.example.com/logo.png"


@pytest.mark.asyncio
async def test_upload_object_route_rejects_non_image_content_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def _fake_upload_object_bytes(*_: object, **__: object) -> None:
        nonlocal called
        called = True
        raise AssertionError(
            "upload_object_bytes should not be called for non-image uploads"
        )

    monkeypatch.setattr(
        storage_routes, "upload_object_bytes", _fake_upload_object_bytes
    )

    payload = UploadObjectRequest(
        purpose="tenant-logo",
        file_name="logo.txt",
        content_type="text/plain",
        content_base64=base64.b64encode(b"plain-text").decode("ascii"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await storage_routes.upload_object(payload, tenant_id="tenant-1")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Only image uploads are supported"
    assert called is False


@pytest.mark.asyncio
async def test_upload_object_route_infers_image_content_type_from_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_upload_object_bytes(
        *,
        purpose: str,
        tenant_id: str,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
    ) -> SimpleNamespace:
        captured.update(
            purpose=purpose,
            tenant_id=tenant_id,
            file_name=file_name,
            content_type=content_type,
            file_bytes=file_bytes,
        )
        return SimpleNamespace(
            bucket="supacrm",
            object_key="product-images/tenant-1/image.png",
            download_url="https://cdn.example.com/image.png",
        )

    monkeypatch.setattr(
        storage_routes, "upload_object_bytes", _fake_upload_object_bytes
    )

    payload = UploadObjectRequest(
        purpose="product-image",
        file_name="image.png",
        content_type="",
        content_base64=base64.b64encode(b"product-bytes").decode("ascii"),
    )
    response = await storage_routes.upload_object(payload, tenant_id="tenant-1")

    assert captured["content_type"] == "image/png"
    assert response.file_key == "product-images/tenant-1/image.png"
    assert response.file_url == "https://cdn.example.com/image.png"


@pytest.mark.asyncio
async def test_upload_object_route_uses_local_fallback_when_minio_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(storage_service.settings, "ENV", "dev")
    monkeypatch.setattr(
        storage_service.settings, "APP_BASE_URL", "http://localhost:8000"
    )
    monkeypatch.setattr(storage_service, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")

    def _raise_unavailable() -> None:
        raise ConnectionError("MinIO unavailable")

    monkeypatch.setattr(storage_service, "_get_client", _raise_unavailable)

    payload = UploadObjectRequest(
        purpose="tenant-logo",
        file_name="logo.png",
        content_type="image/png",
        content_base64=base64.b64encode(b"logo-bytes").decode("ascii"),
    )
    response = await storage_routes.upload_object(payload, tenant_id="tenant-1")

    assert response.file_key.startswith("tenant-logos/tenant-1/")
    assert response.file_url.startswith(
        "http://127.0.0.1:8000/media/tenant-logos/tenant-1/"
    )
    assert (
        storage_service.LOCAL_UPLOAD_ROOT / response.file_key
    ).read_bytes() == b"logo-bytes"


@pytest.mark.asyncio
async def test_upload_object_bytes_falls_back_to_local_filesystem_when_minio_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(storage_service.settings, "ENV", "dev")
    monkeypatch.setattr(
        storage_service.settings, "APP_BASE_URL", "http://localhost:8000"
    )
    monkeypatch.setattr(storage_service, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")

    def _raise_unavailable() -> None:
        raise ConnectionError("MinIO unavailable")

    monkeypatch.setattr(storage_service, "_get_client", _raise_unavailable)

    result = storage_service.upload_object_bytes(
        purpose="tenant-logo",
        tenant_id="tenant-1",
        file_name="logo.png",
        content_type="image/png",
        file_bytes=b"logo-bytes",
    )

    stored_path = storage_service.LOCAL_UPLOAD_ROOT / result.object_key
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"logo-bytes"
    assert result.bucket == storage_service.settings.MINIO_BUCKET
    assert result.download_url.startswith(
        "http://127.0.0.1:8000/media/tenant-logos/tenant-1/"
    )
    assert result.download_url.endswith("logo.png")


@pytest.mark.asyncio
async def test_upload_object_bytes_uses_local_media_url_in_dev_even_when_minio_is_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(storage_service.settings, "ENV", "dev")
    monkeypatch.setattr(
        storage_service.settings, "APP_BASE_URL", "http://localhost:8000"
    )
    monkeypatch.setattr(storage_service, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")

    class _FakeClient:
        def bucket_exists(self, bucket_name: str) -> bool:
            _ = bucket_name
            return True

        def make_bucket(self, bucket_name: str) -> None:
            _ = bucket_name

        def put_object(
            self,
            bucket_name: str,
            object_key: str,
            stream,
            length: int,
            content_type: str,
        ) -> None:
            _ = (bucket_name, object_key, stream, length, content_type)

        def presigned_get_object(
            self, bucket_name: str, object_key: str, expires
        ) -> str:
            _ = (bucket_name, object_key, expires)
            return "https://minio.internal.example/object"

    monkeypatch.setattr(storage_service, "_get_client", lambda: _FakeClient())

    result = storage_service.upload_object_bytes(
        purpose="product-image",
        tenant_id="tenant-1",
        file_name="photo.png",
        content_type="image/png",
        file_bytes=b"image-bytes",
    )

    assert result.download_url.startswith(
        "http://127.0.0.1:8000/media/product-images/tenant-1/"
    )
    assert result.download_url.endswith("photo.png")
    assert (
        storage_service.LOCAL_UPLOAD_ROOT / result.object_key
    ).read_bytes() == b"image-bytes"


@pytest.mark.asyncio
async def test_presign_download_url_falls_back_to_local_media_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_service.settings, "ENV", "dev")
    monkeypatch.setattr(
        storage_service.settings, "APP_BASE_URL", "http://localhost:8000"
    )

    def _raise_unavailable() -> None:
        raise ConnectionError("MinIO unavailable")

    monkeypatch.setattr(storage_service, "_get_client", _raise_unavailable)

    url = storage_service.presign_download_url("tenant-logos/tenant-1/logo.png")

    assert url == "http://127.0.0.1:8000/media/tenant-logos/tenant-1/logo.png"


@pytest.mark.asyncio
async def test_presign_download_url_prefers_local_media_when_file_exists_in_dev(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(storage_service.settings, "ENV", "dev")
    monkeypatch.setattr(
        storage_service.settings, "APP_BASE_URL", "http://localhost:8000"
    )
    monkeypatch.setattr(storage_service, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")

    stored_path = storage_service.LOCAL_UPLOAD_ROOT / "tenant-logos/tenant-1/logo.png"
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(b"logo-bytes")

    class _FakeClient:
        def bucket_exists(self, bucket_name: str) -> bool:
            _ = bucket_name
            return True

        def make_bucket(self, bucket_name: str) -> None:
            _ = bucket_name

        def presigned_get_object(
            self, bucket_name: str, object_key: str, expires
        ) -> str:
            _ = (bucket_name, object_key, expires)
            return "https://minio.internal.example/object"

    monkeypatch.setattr(storage_service, "_get_client", lambda: _FakeClient())

    url = storage_service.presign_download_url("tenant-logos/tenant-1/logo.png")

    assert url == "http://127.0.0.1:8000/media/tenant-logos/tenant-1/logo.png"


def test_create_app_mounts_local_media_in_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main.settings, "ENV", "dev")

    app = create_app()
    media_mounts = [
        route for route in app.routes if getattr(route, "path", None) == "/media"
    ]

    assert media_mounts, "Expected /media static mount in dev mode"


def test_media_static_file_is_public_in_dev_without_tenant_header(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_main.settings, "ENV", "dev")
    monkeypatch.setattr(app_main, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(storage_service, "LOCAL_UPLOAD_ROOT", tmp_path / "uploads")

    async def _noop_init_db() -> None:
        return None

    async def _noop_run_migrations() -> None:
        return None

    monkeypatch.setattr(app_main, "init_db", _noop_init_db)
    monkeypatch.setattr(app_main, "run_database_migrations", _noop_run_migrations)

    object_key = "tenant-logos/supacrm-test/b684f9da14b6447d9ef13d2cc5bf3fb5-logo.png"
    stored_path = app_main.LOCAL_UPLOAD_ROOT / object_key
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(b"\x89PNG\r\n\x1a\nlogo-bytes")

    app = create_app()
    with TestClient(app) as client:
        response = client.get(f"/media/{object_key}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == b"\x89PNG\r\n\x1a\nlogo-bytes"


@pytest.mark.asyncio
async def test_run_database_migrations_targets_head_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeConfig:
        def __init__(self, ini_path: str) -> None:
            captured["ini_path"] = ini_path

    async def _immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    def _fake_upgrade(config: object, revision: str) -> None:
        captured["config"] = config
        captured["revision"] = revision

    monkeypatch.setattr(app_db, "Config", _FakeConfig)
    monkeypatch.setattr(app_db.command, "upgrade", _fake_upgrade)
    monkeypatch.setattr(app_db.asyncio, "to_thread", _immediate_to_thread)

    await app_db.run_database_migrations()

    assert str(captured["ini_path"]).endswith("backend/alembic.ini")
    assert captured["revision"] == "head"


@pytest.mark.asyncio
async def test_update_current_tenant_branding_trims_logo_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_update_tenant_branding_logo(
        db: object,
        *,
        tenant_id: str,
        logo_file_key: str | None,
    ) -> TenantBrandingDetails:
        _ = db
        captured["tenant_id"] = tenant_id
        captured["logo_file_key"] = logo_file_key
        return TenantBrandingDetails(
            tenant_id=tenant_id,
            logo_file_key=logo_file_key,
            logo_url="https://cdn.example.com/logo.png" if logo_file_key else None,
            brand_primary_color=None,
            brand_secondary_color=None,
            sidebar_background_color=None,
            sidebar_text_color=None,
        )

    monkeypatch.setattr(
        tenant_routes,
        "update_tenant_branding_logo",
        _fake_update_tenant_branding_logo,
    )

    response = await tenant_routes.update_current_tenant_branding(
        TenantBrandingUpdateRequest(logo_file_key="  media/logo.png  "),
        tenant_id="tenant-1",
        db=object(),
    )

    assert captured == {"tenant_id": "tenant-1", "logo_file_key": "media/logo.png"}
    assert response.logo_file_key == "media/logo.png"
    assert response.logo_url == "https://cdn.example.com/logo.png"


@pytest.mark.asyncio
async def test_get_marketing_integrations_route_returns_persisted_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_marketing_integrations(
        *_: object, **__: object
    ) -> MarketingIntegrationsDetails:
        return MarketingIntegrationsDetails(
            whatsapp=WhatsAppIntegrationDetails(
                business_account_id="123",
                phone_number_id="456",
                display_name="SupaCRM",
                access_token_set=True,
                webhook_verify_token_set=True,
                is_enabled=True,
                updated_at=datetime.now(timezone.utc),
            ),
            smtp=SmtpSettingsDetails(
                smtp_host="smtp.example.com",
                smtp_port=587,
                smtp_username="mailer",
                from_email="no-reply@example.com",
                from_name="Growth Team",
                use_tls=True,
                use_ssl=False,
                password_set=True,
                is_enabled=True,
                updated_at=datetime.now(timezone.utc),
            ),
            social=[],
        )

    monkeypatch.setattr(
        marketing_routes,
        "get_marketing_integrations",
        _fake_get_marketing_integrations,
    )

    response = await marketing_routes.get_marketing_integrations_route(
        tenant_id="tenant-1",
        db=object(),
    )

    assert response.whatsapp.business_account_id == "123"
    assert response.whatsapp.access_token_set is True
    assert response.smtp.smtp_host == "smtp.example.com"
    assert response.smtp.password_set is True
    assert response.smtp.from_name == "Growth Team"
    assert response.social == []


@pytest.mark.asyncio
async def test_update_whatsapp_integration_route_persists_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_update_whatsapp_settings(
        db: object,
        *,
        tenant_id: str,
        business_account_id: str | None,
        phone_number_id: str | None,
        display_name: str | None,
        access_token: str | None,
        webhook_verify_token: str | None,
        is_enabled: bool,
    ) -> WhatsAppIntegrationDetails:
        captured.update(
            tenant_id=tenant_id,
            business_account_id=business_account_id,
            phone_number_id=phone_number_id,
            display_name=display_name,
            access_token=access_token,
            webhook_verify_token=webhook_verify_token,
            is_enabled=is_enabled,
        )
        return WhatsAppIntegrationDetails(
            business_account_id=business_account_id,
            phone_number_id=phone_number_id,
            display_name=display_name,
            access_token_set=bool(access_token),
            webhook_verify_token_set=bool(webhook_verify_token),
            is_enabled=is_enabled,
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        marketing_routes,
        "update_whatsapp_settings",
        _fake_update_whatsapp_settings,
    )

    response = await marketing_routes.update_whatsapp_integration_route(
        payload=marketing_routes.WhatsAppIntegrationSettingsUpdateRequest(
            business_account_id="123",
            phone_number_id="456",
            display_name="SupaCRM",
            access_token="secret-access-token",
            webhook_verify_token="verify-token",
            is_enabled=True,
        ),
        tenant_id="tenant-1",
        db=object(),
    )

    assert captured == {
        "tenant_id": "tenant-1",
        "business_account_id": "123",
        "phone_number_id": "456",
        "display_name": "SupaCRM",
        "access_token": "secret-access-token",
        "webhook_verify_token": "verify-token",
        "is_enabled": True,
    }
    assert response.access_token_set is True
    assert response.webhook_verify_token_set is True


@pytest.mark.asyncio
async def test_update_smtp_integration_route_persists_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_update_smtp_settings(
        db: object,
        *,
        tenant_id: str,
        smtp_host: str | None,
        smtp_port: int,
        smtp_username: str | None,
        smtp_password: str | None,
        from_email: str | None,
        from_name: str | None,
        use_tls: bool,
        use_ssl: bool,
        is_enabled: bool,
    ) -> SmtpSettingsDetails:
        captured.update(
            tenant_id=tenant_id,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            from_name=from_name,
            use_tls=use_tls,
            use_ssl=use_ssl,
            is_enabled=is_enabled,
        )
        return SmtpSettingsDetails(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            from_email=from_email,
            from_name=from_name,
            use_tls=use_tls,
            use_ssl=use_ssl,
            password_set=bool(smtp_password),
            is_enabled=is_enabled,
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        marketing_routes,
        "update_smtp_settings",
        _fake_update_smtp_settings,
    )

    response = await marketing_routes.update_smtp_integration_route(
        payload=marketing_routes.SmtpSettingsUpdateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="mailer",
            smtp_password="secret-password",
            from_email="no-reply@example.com",
            from_name="Growth Team",
            use_tls=True,
            use_ssl=False,
            is_enabled=True,
        ),
        tenant_id="tenant-1",
        db=object(),
    )

    assert captured == {
        "tenant_id": "tenant-1",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "mailer",
        "smtp_password": "secret-password",
        "from_email": "no-reply@example.com",
        "from_name": "Growth Team",
        "use_tls": True,
        "use_ssl": False,
        "is_enabled": True,
    }
    assert response.password_set is True
    assert response.smtp_host == "smtp.example.com"
    assert response.from_name == "Growth Team"
