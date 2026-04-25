from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.auth import service as auth_service
from app.crm import routes as crm_routes
from app.crm.service import CompanyDetails
from app.core.security.deps import get_current_principal
from app.db_deps import get_auth_db
from app.main import create_app
from app.tenants import routes as tenant_routes
from app.tenants import service as tenant_service


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeResult:
    def __init__(
        self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise AssertionError("Expected scalar result but found none")
        return self._scalar


@dataclass
class FakeAsyncSession:
    tenant_id: str = "tenant-alpha"
    user_id: str = "user-alpha"
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_images: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    audit_entries: list[Any] = field(default_factory=list)
    request_commits: int = 0
    request_rollbacks: int = 0
    commit_calls: int = 0
    rollback_calls: int = 0
    begin_calls: int = 0
    close_calls: int = 0

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select exists (" in sql and "from public.tenant_user_roles tur" in sql:
            return _FakeResult(scalar=True)

        if "select p.id from public.products p" in sql and "upper(p.sku) = :sku" in sql:
            tenant_id = str(payload["tenant_id"])
            sku = str(payload["sku"]).upper()
            exclude_id = payload.get("exclude_product_id")
            for product_id, product in self.products.items():
                if product["tenant_id"] != tenant_id:
                    continue
                if str(product["sku"]).upper() != sku:
                    continue
                if exclude_id is not None and str(product_id) == str(exclude_id):
                    continue
                return _FakeResult(scalar=product_id)
            return _FakeResult(scalar=None)

        if "insert into public.products (" in sql:
            now = datetime.now(timezone.utc)
            product_id = str(payload["id"])
            self.products[product_id] = {
                "id": product_id,
                "tenant_id": str(payload["tenant_id"]),
                "name": str(payload["name"]),
                "sku": str(payload["sku"]),
                "description": payload.get("description"),
                "unit_price": Decimal(payload["unit_price"]),
                "currency": str(payload["currency"]),
                "is_active": bool(payload["is_active"]),
                "created_at": now,
                "updated_at": now,
            }
            self.product_images.setdefault(product_id, [])
            return _FakeResult()

        if "insert into public.product_images (" in sql:
            product_id = str(payload["product_id"])
            self.product_images.setdefault(product_id, []).append(
                {
                    "id": str(payload["id"]),
                    "tenant_id": str(payload["tenant_id"]),
                    "product_id": product_id,
                    "position": int(payload["position"]),
                    "file_key": str(payload["file_key"]),
                    "created_at": datetime.now(timezone.utc),
                }
            )
            return _FakeResult()

        if (
            "from public.products p" in sql
            and "where p.tenant_id = cast(:tenant_id as varchar)" in sql
        ):
            tenant_id = str(payload["tenant_id"])
            if "and p.id = cast(:product_id as varchar)" in sql:
                product_id = str(payload["product_id"])
                product = self.products.get(product_id)
                if not product or product["tenant_id"] != tenant_id:
                    return _FakeResult(rows=[])
                return _FakeResult(rows=[dict(product)])

            rows = [
                dict(product)
                for product in self.products.values()
                if product["tenant_id"] == tenant_id
            ]
            rows.sort(key=lambda row: (-row["created_at"].timestamp(), row["name"]))
            return _FakeResult(rows=rows)

        if "from public.product_images pi" in sql:
            tenant_id = str(payload["tenant_id"])
            product_id = str(payload["product_id"])
            rows = [
                dict(row)
                for row in self.product_images.get(product_id, [])
                if row["tenant_id"] == tenant_id
            ]
            rows.sort(key=lambda row: row["position"])
            return _FakeResult(rows=rows)

        if "update public.products" in sql:
            product_id = str(payload["product_id"])
            product = self.products.get(product_id)
            if not product:
                return _FakeResult()
            product["name"] = str(payload["name"])
            product["sku"] = str(payload["sku"])
            product["description"] = payload.get("description")
            product["unit_price"] = Decimal(payload["unit_price"])
            product["currency"] = str(payload["currency"])
            product["is_active"] = bool(payload["is_active"])
            product["updated_at"] = datetime.now(timezone.utc)
            return _FakeResult()

        if "delete from public.product_images" in sql:
            product_id = str(payload["product_id"])
            self.product_images[product_id] = []
            return _FakeResult()

        if "delete from public.products" in sql:
            product_id = str(payload["product_id"])
            self.products.pop(product_id, None)
            self.product_images.pop(product_id, None)
            return _FakeResult()

        raise AssertionError(f"Unhandled SQL in fake session: {sql}")

    async def commit(self) -> None:
        self.commit_calls += 1
        raise AssertionError(
            "Service-level commit() is not allowed in request-owned transaction tests"
        )

    async def rollback(self) -> None:
        self.rollback_calls += 1
        raise AssertionError(
            "Service-level rollback() is not allowed in request-owned transaction tests"
        )

    async def begin(self) -> None:
        self.begin_calls += 1
        raise AssertionError(
            "Service-level begin() is not allowed in request-owned transaction tests"
        )

    async def close(self) -> None:
        self.close_calls += 1
        raise AssertionError(
            "Service-level close() is not allowed in request-owned transaction tests"
        )

    def add(self, instance: Any) -> None:
        self.audit_entries.append(instance)


@pytest.fixture
def fake_db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest_asyncio.fixture
async def client(fake_db: FakeAsyncSession):
    app = create_app()

    async def _override_principal() -> dict[str, Any]:
        return {
            "sub": fake_db.user_id,
            "tenant_id": fake_db.tenant_id,
            "tenant_status": "active",
        }

    async def _override_auth_db():
        try:
            yield fake_db
            fake_db.request_commits += 1
        except Exception:
            fake_db.request_rollbacks += 1
            raise

    app.dependency_overrides[get_current_principal] = _override_principal
    app.dependency_overrides[get_auth_db] = _override_auth_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


def _auth_headers(tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer integration-test-token",
        "X-Tenant-Id": tenant_id,
    }


def _company_details(
    *,
    company_id: str,
    tenant_id: str,
    name: str,
    website: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    industry: str | None = None,
    address: str | None = None,
    vat_number: str | None = None,
    registration_number: str | None = None,
    notes: str | None = None,
) -> CompanyDetails:
    now = datetime.now(timezone.utc)
    return CompanyDetails(
        id=company_id,
        tenant_id=tenant_id,
        name=name,
        website=website,
        email=email,
        phone=phone,
        industry=industry,
        address=address,
        vat_number=vat_number,
        registration_number=registration_number,
        notes=notes,
        created_at=now,
        updated_at=now,
    )


def _product_images(
    count: int,
    *,
    prefix: str = "products",
    wrap_positions: bool = False,
) -> list[dict[str, Any]]:
    return [
        {
            "position": position if not wrap_positions or position <= 15 else 15,
            "file_key": f"{prefix}/image-{position}.png",
        }
        for position in range(1, count + 1)
    ]


def _product_images_in_order(
    positions: list[int],
    *,
    prefix: str = "products",
) -> list[dict[str, Any]]:
    return [
        {
            "position": position,
            "file_key": f"{prefix}/image-{position}.png",
        }
        for position in positions
    ]


@pytest.mark.asyncio
async def test_catalog_create_update_delete_uses_request_owned_transaction(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    create_response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Starter Product",
            "sku": "sku-001",
            "description": "Initial",
            "unit_price": "19.99",
            "currency": "usd",
            "is_active": True,
            "images": _product_images_in_order([3, 1, 2], prefix="products/starter"),
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["tenant_id"] == fake_db.tenant_id
    assert created["sku"] == "SKU-001"
    assert [image["position"] for image in created["images"]] == [1, 2, 3]
    assert [image["file_key"] for image in created["images"]] == [
        "products/starter/image-1.png",
        "products/starter/image-2.png",
        "products/starter/image-3.png",
    ]
    product_id = created["id"]

    get_response = await client.get(f"/products/{product_id}", headers=headers)
    assert get_response.status_code == 200
    assert [image["position"] for image in get_response.json()["images"]] == [1, 2, 3]

    update_response = await client.put(
        f"/products/{product_id}",
        headers=headers,
        json={
            "name": "Starter Product Updated",
            "sku": "sku-001",
            "description": "Updated",
            "unit_price": "24.99",
            "currency": "usd",
            "is_active": False,
            "images": _product_images_in_order([2, 3, 1], prefix="products/starter-new"),
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Starter Product Updated"
    assert updated["is_active"] is False
    assert [image["position"] for image in updated["images"]] == [1, 2, 3]
    assert [image["file_key"] for image in updated["images"]] == [
        "products/starter-new/image-1.png",
        "products/starter-new/image-2.png",
        "products/starter-new/image-3.png",
    ]

    refreshed_response = await client.get(f"/products/{product_id}", headers=headers)
    assert refreshed_response.status_code == 200
    assert [image["position"] for image in refreshed_response.json()["images"]] == [1, 2, 3]

    delete_response = await client.delete(f"/products/{product_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True

    assert fake_db.request_commits >= 3
    assert fake_db.request_rollbacks == 0
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0
    assert fake_db.begin_calls == 0
    assert fake_db.close_calls == 0


@pytest.mark.asyncio
async def test_catalog_duplicate_sku_triggers_request_rollback(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    first_response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Primary Product",
            "sku": "dup-sku",
            "description": "First",
            "unit_price": "10.00",
            "currency": "usd",
            "is_active": True,
            "images": _product_images(3, prefix="products/first"),
        },
    )
    assert first_response.status_code == 201

    rollbacks_before = fake_db.request_rollbacks
    duplicate_response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Duplicate Product",
            "sku": "DUP-SKU",
            "description": "Second",
            "unit_price": "12.00",
            "currency": "usd",
            "is_active": True,
            "images": _product_images(3, prefix="products/second"),
        },
    )
    assert duplicate_response.status_code == 400
    assert "already exists" in duplicate_response.json()["error"]["message"].lower()

    assert fake_db.request_rollbacks >= rollbacks_before + 1
    assert len(fake_db.products) == 1
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_catalog_rejects_fewer_than_three_images(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Too Few Images",
            "sku": "few-images",
            "description": "Invalid",
            "unit_price": "9.99",
            "currency": "usd",
            "is_active": True,
            "images": _product_images(2, prefix="products/few"),
        },
    )

    assert response.status_code == 422
    assert "At least 3 product images are required" in str(response.json())
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_catalog_rejects_more_than_fifteen_images(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Too Many Images",
            "sku": "many-images",
            "description": "Invalid",
            "unit_price": "9.99",
            "currency": "usd",
            "is_active": True,
            "images": _product_images(
                16,
                prefix="products/many",
                wrap_positions=True,
            ),
        },
    )

    assert response.status_code == 422
    assert "Maximum 15 product images are allowed" in str(response.json())
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_catalog_accepts_fifteen_images(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    response = await client.post(
        "/products",
        headers=headers,
        json={
            "name": "Fifteen Images",
            "sku": "fifteen-images",
            "description": "Valid",
            "unit_price": "29.99",
            "currency": "usd",
            "is_active": True,
            "images": _product_images(15, prefix="products/fifteen"),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload["images"]) == 15
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_auth_whoami_uses_injected_request_db(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    def _fail_factory() -> Any:
        raise AssertionError("Protected whoami flow must not open replacement sessions")

    called: dict[str, bool] = {"tenant": False, "identity": False, "roles": False}

    async def _fake_get_tenant_state(session: Any, tenant_id: str) -> dict[str, Any]:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        called["tenant"] = True
        return {"id": tenant_id, "is_active": True, "status": "active"}

    async def _fake_get_identity_by_user_id(
        session: Any, tenant_id: str, user_id: str
    ) -> dict[str, Any]:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert user_id == fake_db.user_id
        called["identity"] = True
        return {
            "email": "owner@example.com",
            "full_name": "Owner User",
            "is_owner": True,
            "user_is_active": True,
            "membership_is_active": True,
        }

    async def _fake_get_role_names(
        session: Any, tenant_id: str, user_id: str
    ) -> list[str]:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert user_id == fake_db.user_id
        called["roles"] = True
        return ["tenant.admin"]

    monkeypatch.setattr(auth_service, "async_session_factory", _fail_factory)
    monkeypatch.setattr(auth_service, "_get_tenant_state", _fake_get_tenant_state)
    monkeypatch.setattr(
        auth_service, "_get_identity_by_user_id", _fake_get_identity_by_user_id
    )
    monkeypatch.setattr(auth_service, "_get_role_names", _fake_get_role_names)

    response = await client.get("/auth/whoami", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["tenant_id"] == fake_db.tenant_id
    assert payload["user_id"] == fake_db.user_id
    assert payload["roles"] == ["tenant.admin"]
    assert called == {"tenant": True, "identity": True, "roles": True}
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_auth_logout_uses_injected_request_db(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    refresh_token = "refresh-token-success"
    expected_hash = auth_service._hash_token(refresh_token)

    def _fail_factory() -> Any:
        raise AssertionError("Protected logout flow must not open replacement sessions")

    calls: dict[str, Any] = {"revoke_token": False, "revoke_family": False}

    def _fake_decode_refresh_token(token: str) -> dict[str, str]:
        assert token == refresh_token
        return {
            "sub": fake_db.user_id,
            "tenant_id": fake_db.tenant_id,
            "jti": "token-1",
            "family_id": "family-1",
        }

    async def _fake_get_refresh_token_record(
        session: Any, token_id: str
    ) -> dict[str, str]:
        assert session is fake_db
        assert token_id == "token-1"
        return {"token_hash": expected_hash}

    async def _fake_revoke_refresh_token(
        session: Any,
        *,
        tenant_id: str,
        token_id: str,
        reason: str,
        now: datetime,
    ) -> None:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert token_id == "token-1"
        assert reason == "logout"
        assert isinstance(now, datetime)
        calls["revoke_token"] = True

    async def _fake_revoke_refresh_family(*args: Any, **kwargs: Any) -> None:
        calls["revoke_family"] = True

    monkeypatch.setattr(auth_service, "async_session_factory", _fail_factory)
    monkeypatch.setattr(
        auth_service, "decode_refresh_token", _fake_decode_refresh_token
    )
    monkeypatch.setattr(
        auth_service, "_get_refresh_token_record", _fake_get_refresh_token_record
    )
    monkeypatch.setattr(
        auth_service, "_revoke_refresh_token", _fake_revoke_refresh_token
    )
    monkeypatch.setattr(
        auth_service, "_revoke_refresh_family", _fake_revoke_refresh_family
    )

    response = await client.post(
        "/auth/logout",
        headers=headers,
        json={"refresh_token": refresh_token, "revoke_family": False},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert calls == {"revoke_token": True, "revoke_family": False}
    assert len(fake_db.audit_entries) == 1
    audit_entry = fake_db.audit_entries[0]
    assert getattr(audit_entry, "tenant_id") == fake_db.tenant_id
    assert getattr(audit_entry, "actor_user_id") == fake_db.user_id
    assert getattr(audit_entry, "action") == "auth.logout.succeeded"
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_auth_logout_failure_marks_request_rollback(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    refresh_token = "refresh-token-invalid"

    def _fail_factory() -> Any:
        raise AssertionError("Protected logout flow must not open replacement sessions")

    def _fake_decode_refresh_token(token: str) -> dict[str, str]:
        assert token == refresh_token
        return {
            "sub": fake_db.user_id,
            "tenant_id": fake_db.tenant_id,
            "jti": "token-missing",
            "family_id": "family-1",
        }

    async def _fake_get_refresh_token_record(session: Any, token_id: str) -> None:
        assert session is fake_db
        assert token_id == "token-missing"
        return None

    audit_called = {"value": False}

    async def _fake_write_audit_log(**kwargs: Any) -> None:
        audit_called["value"] = True

    monkeypatch.setattr(auth_service, "async_session_factory", _fail_factory)
    monkeypatch.setattr(
        auth_service, "decode_refresh_token", _fake_decode_refresh_token
    )
    monkeypatch.setattr(
        auth_service, "_get_refresh_token_record", _fake_get_refresh_token_record
    )
    monkeypatch.setattr(auth_service, "_write_audit_log", _fake_write_audit_log)

    rollbacks_before = fake_db.request_rollbacks
    response = await client.post(
        "/auth/logout",
        headers=headers,
        json={"refresh_token": refresh_token, "revoke_family": False},
    )
    assert response.status_code == 401
    assert "invalid refresh token" in response.json()["error"]["message"].lower()
    assert fake_db.request_rollbacks >= rollbacks_before + 1
    assert audit_called["value"] is False
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_tenant_membership_patch_uses_injected_request_db(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    async def _fake_update_tenant_membership(
        session: Any,
        *,
        tenant_id: str,
        user_id: str,
        membership_is_active: bool | None = None,
        is_owner: bool | None = None,
        transfer_owner_from_user_id: str | None = None,
    ) -> Any:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert user_id == "user-target"
        assert membership_is_active is False
        assert is_owner is None
        assert transfer_owner_from_user_id is None
        return tenant_service.TenantMembershipMutationResult(
            tenant_id=tenant_id,
            user_id=user_id,
            membership_is_active=False,
            is_owner=False,
            transferred_owner_from_user_id=None,
        )

    monkeypatch.setattr(
        tenant_routes,
        "update_tenant_membership",
        _fake_update_tenant_membership,
    )

    response = await client.patch(
        "/tenants/me/users/user-target/membership",
        headers=headers,
        json={"membership_is_active": False},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": fake_db.tenant_id,
        "user_id": "user-target",
        "membership_is_active": False,
        "is_owner": False,
        "transferred_owner_from_user_id": None,
    }
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_tenant_membership_delete_uses_injected_request_db(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)

    async def _fake_remove_tenant_membership(
        session: Any,
        *,
        tenant_id: str,
        user_id: str,
    ) -> Any:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert user_id == "user-target"
        return tenant_service.TenantMembershipRemovalResult(
            tenant_id=tenant_id,
            user_id=user_id,
            removed=True,
        )

    monkeypatch.setattr(
        tenant_routes,
        "remove_tenant_membership",
        _fake_remove_tenant_membership,
    )

    response = await client.delete(
        "/tenants/me/users/user-target/membership",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": fake_db.tenant_id,
        "user_id": "user-target",
        "removed": True,
    }
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_company_create_forwards_extended_fields(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    company_id = f"cmp_{uuid.uuid4().hex[:12]}"
    payload = {
        "name": "Forwarded Company",
        "website": "https://forwarded.example",
        "email": "billing@example.com",
        "phone": "+1-555-0100",
        "industry": "Technology",
        "address": "123 Market Street, Suite 500",
        "vat_number": "VAT-12345",
        "registration_number": "REG-67890",
        "notes": "Created via regression test",
    }

    async def _fake_create_company(
        session: Any,
        *,
        tenant_id: str,
        name: str,
        website: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        industry: str | None = None,
        address: str | None = None,
        vat_number: str | None = None,
        registration_number: str | None = None,
        notes: str | None = None,
    ) -> CompanyDetails:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert name == payload["name"]
        assert website == payload["website"]
        assert email == payload["email"]
        assert phone == payload["phone"]
        assert industry == payload["industry"]
        assert address == payload["address"]
        assert vat_number == payload["vat_number"]
        assert registration_number == payload["registration_number"]
        assert notes == payload["notes"]
        return _company_details(
            company_id=company_id,
            tenant_id=tenant_id,
            name=name,
            website=website,
            email=email,
            phone=phone,
            industry=industry,
            address=address,
            vat_number=vat_number,
            registration_number=registration_number,
            notes=notes,
        )

    monkeypatch.setattr(crm_routes, "create_company", _fake_create_company)

    response = await client.post("/crm/companies", headers=headers, json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == company_id
    assert body["tenant_id"] == fake_db.tenant_id
    assert body["name"] == payload["name"]
    assert body["address"] == payload["address"]
    assert body["vat_number"] == payload["vat_number"]
    assert body["registration_number"] == payload["registration_number"]
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_company_read_returns_extended_fields(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    company_id = f"cmp_{uuid.uuid4().hex[:12]}"
    company = _company_details(
        company_id=company_id,
        tenant_id=fake_db.tenant_id,
        name="Readable Company",
        website="https://readable.example",
        email="owner@readable.example",
        phone="+1-555-0200",
        industry="Services",
        address="500 Read Street",
        vat_number="VAT-READ-1",
        registration_number="REG-READ-2",
        notes="Loaded from backend",
    )

    async def _fake_get_company_by_id(
        session: Any,
        *,
        tenant_id: str,
        company_id: str,
    ) -> CompanyDetails | None:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert company_id == company.id
        return company

    monkeypatch.setattr(crm_routes, "get_company_by_id", _fake_get_company_by_id)

    response = await client.get(f"/crm/companies/{company_id}", headers=headers)
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == company.id
    assert body["address"] == company.address
    assert body["vat_number"] == company.vat_number
    assert body["registration_number"] == company.registration_number
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_company_update_forwards_extended_fields(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    expected_company_id = f"cmp_{uuid.uuid4().hex[:12]}"
    payload = {
        "name": "Updated Company",
        "website": "https://updated.example",
        "email": "accounts@example.com",
        "phone": "+1-555-0300",
        "industry": "Manufacturing",
        "address": "900 Updated Avenue",
        "vat_number": "VAT-54321",
        "registration_number": "REG-09876",
        "notes": "Updated via regression test",
    }

    async def _fake_update_company(
        session: Any,
        *,
        tenant_id: str,
        company_id: str,
        name: str | None = None,
        website: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        industry: str | None = None,
        address: str | None = None,
        vat_number: str | None = None,
        registration_number: str | None = None,
        notes: str | None = None,
    ) -> CompanyDetails:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert company_id == expected_company_id
        assert name == payload["name"]
        assert website == payload["website"]
        assert email == payload["email"]
        assert phone == payload["phone"]
        assert industry == payload["industry"]
        assert address == payload["address"]
        assert vat_number == payload["vat_number"]
        assert registration_number == payload["registration_number"]
        assert notes == payload["notes"]
        return _company_details(
            company_id=company_id,
            tenant_id=tenant_id,
            name=name or "",
            website=website,
            email=email,
            phone=phone,
            industry=industry,
            address=address,
            vat_number=vat_number,
            registration_number=registration_number,
            notes=notes,
        )

    monkeypatch.setattr(crm_routes, "update_company", _fake_update_company)

    response = await client.patch(
        f"/crm/companies/{expected_company_id}",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == expected_company_id
    assert body["address"] == payload["address"]
    assert body["vat_number"] == payload["vat_number"]
    assert body["registration_number"] == payload["registration_number"]
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_contact_delete_returns_success_and_passes_tenant_context(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    expected_contact_id = f"cnt_{uuid.uuid4().hex[:12]}"

    async def _fake_delete_contact(
        session: Any,
        *,
        tenant_id: str,
        contact_id: str,
    ) -> bool:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert contact_id == expected_contact_id
        return True

    monkeypatch.setattr(crm_routes, "delete_contact", _fake_delete_contact)

    response = await client.delete(f"/crm/contacts/{expected_contact_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Contact deleted successfully"
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_company_delete_returns_success_and_passes_tenant_context(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    expected_company_id = f"cmp_{uuid.uuid4().hex[:12]}"

    async def _fake_delete_company(
        session: Any,
        *,
        tenant_id: str,
        company_id: str,
    ) -> bool:
        assert session is fake_db
        assert tenant_id == fake_db.tenant_id
        assert company_id == expected_company_id
        return True

    monkeypatch.setattr(crm_routes, "delete_company", _fake_delete_company)

    response = await client.delete(f"/crm/companies/{expected_company_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Company deleted successfully"
    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0


@pytest.mark.asyncio
async def test_contact_delete_returns_conflict_when_related_records_exist(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    contact_id = f"cnt_{uuid.uuid4().hex[:12]}"

    async def _fake_delete_contact(
        session: Any,
        *,
        tenant_id: str,
        contact_id: str,
    ) -> bool:
        raise IntegrityError("delete", {}, Exception("fk_contacts_deals"))

    monkeypatch.setattr(crm_routes, "delete_contact", _fake_delete_contact)

    response = await client.delete(f"/crm/contacts/{contact_id}", headers=headers)
    assert response.status_code == 409
    assert "referenced by one or more records" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_company_delete_returns_conflict_when_related_records_exist(
    client: AsyncClient,
    fake_db: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(fake_db.tenant_id)
    company_id = f"cmp_{uuid.uuid4().hex[:12]}"

    async def _fake_delete_company(
        session: Any,
        *,
        tenant_id: str,
        company_id: str,
    ) -> bool:
        raise IntegrityError("delete", {}, Exception("fk_companies_deals"))

    monkeypatch.setattr(crm_routes, "delete_company", _fake_delete_company)

    response = await client.delete(f"/crm/companies/{company_id}", headers=headers)
    assert response.status_code == 409
    assert "referenced by one or more records" in response.json()["error"]["message"]
