from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.internal import bootstrap_routes
from app.commercial import service as commercial_service
from app.tenants import service as tenant_service


class _FakeRowResult:
    def __init__(self, row: dict[str, object] | None):
        self._row = row

    def mappings(self) -> "_FakeRowResult":
        return self

    def first(self) -> dict[str, object] | None:
        return self._row


class _FakeSession:
    def __init__(self, row: dict[str, object] | None):
        self._row = row

    async def execute(self, *_: object, **__: object) -> _FakeRowResult:
        return _FakeRowResult(self._row)


@pytest.mark.asyncio
async def test_tenant_onboarding_summary_reports_ready_state(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = SimpleNamespace(
        id="tenant-1",
        name="Tenant 1",
        is_active=True,
        status="active",
        status_reason=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    users = [
        SimpleNamespace(
            user_id="user-1",
            email="owner@example.com",
            full_name="Owner",
            user_is_active=True,
            membership_is_active=True,
            is_owner=True,
            role_names=["owner", "admin"],
            membership_created_at=datetime.now(timezone.utc),
        )
    ]
    subscription = SimpleNamespace(
        id="sub-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        commercial_state="trial",
        plan_features={"included_capabilities": ["CRM core", "Sales, quotes, and invoices"]},
        trial_end_at=datetime.now(timezone.utc),
        current_period_end_at=datetime.now(timezone.utc),
        grace_end_at=None,
        canceled_at=None,
    )
    plan = SimpleNamespace(features={"included_capabilities": ["CRM core", "Sales, quotes, and invoices"]})

    async def _fake_get_tenant_details(*_: object, **__: object):
        return tenant

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    monkeypatch.setattr(tenant_service, "get_tenant_details", _fake_get_tenant_details)
    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)

    async def _fake_subscription(*_: object, **__: object):
        return subscription

    async def _fake_plan_by_id(*_: object, **__: object):
        return plan

    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_subscription)
    monkeypatch.setattr(commercial_service, "get_plan_by_id", _fake_plan_by_id)

    summary = await tenant_service.get_tenant_onboarding_summary(object(), tenant_id="tenant-1")

    assert summary.tenant.id == "tenant-1"
    assert summary.users_total == 1
    assert summary.owner_count == 1
    assert summary.admin_count == 1
    assert summary.bootstrap_complete is True
    assert summary.ready_for_use is True
    assert summary.missing_steps == []
    assert summary.warnings == []
    assert summary.next_action == "ready"
    assert summary.commercial_subscription is not None
    assert summary.commercial_subscription.commercial_state == "trial"
    assert summary.commercial_subscription.plan_features["included_capabilities"] == [
        "CRM core",
        "Sales, quotes, and invoices",
    ]


@pytest.mark.asyncio
async def test_tenant_onboarding_summary_reports_missing_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = SimpleNamespace(
        id="tenant-1",
        name="Tenant 1",
        is_active=False,
        status="disabled",
        status_reason="pending onboarding",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _fake_get_tenant_details(*_: object, **__: object):
        return tenant

    async def _fake_list_tenant_users(*_: object, **__: object):
        return []

    monkeypatch.setattr(tenant_service, "get_tenant_details", _fake_get_tenant_details)
    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)

    async def _fake_subscription(*_: object, **__: object):
        return None

    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_subscription)

    summary = await tenant_service.get_tenant_onboarding_summary(object(), tenant_id="tenant-1")

    assert summary.bootstrap_complete is False
    assert summary.ready_for_use is False
    assert summary.missing_steps == [
        "tenant_not_active",
        "first_admin_missing",
        "commercial_subscription_missing",
    ]
    assert summary.next_action == "activate_tenant"


@pytest.mark.asyncio
async def test_internal_bootstrap_tenant_route_returns_bootstrap_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeBegin:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeAdminSession:
        def begin(self):
            return _FakeBegin()

    tenant_result = SimpleNamespace(tenant_id="tenant-1", tenant_name="Tenant 1", created_tenant=True)
    rbac_result = SimpleNamespace(created_roles=["owner"], created_permissions=["tenant.admin"])
    admin_result = SimpleNamespace(
        tenant_id="tenant-1",
        user=SimpleNamespace(
            user_id="user-1",
            email="admin@example.com",
            created_user=True,
            created_credentials=True,
            password_set=True,
        ),
        role_assignments=[SimpleNamespace(role_name="admin"), SimpleNamespace(role_name="owner")],
    )

    async def _fake_bootstrap_tenant(*_: object, **__: object):
        return SimpleNamespace(tenant=tenant_result, rbac=rbac_result, admin=admin_result)

    invalidated: list[str] = []

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(bootstrap_routes, "bootstrap_tenant", _fake_bootstrap_tenant)
    monkeypatch.setattr(bootstrap_routes.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    response = await bootstrap_routes.bootstrap_tenant_internal(
        bootstrap_routes.TenantBootstrapRequest(
            tenant_id="tenant-1",
            tenant_name="Tenant 1",
            admin_email="admin@example.com",
            admin_full_name="Admin",
            admin_password="secret",
        ),
        admin_session=_FakeAdminSession(),
    )

    assert response["tenant"]["id"] == "tenant-1"
    assert response["admin"]["user_id"] == "user-1"
    assert response["admin"]["assigned_roles"] == ["admin", "owner"]
    assert invalidated == ["tenant-1"]


@pytest.mark.asyncio
async def test_get_tenant_details_handles_missing_logo_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_tenant_column_exists(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(tenant_service, "_tenant_column_exists", _fake_tenant_column_exists)

    row = {
        "id": "tenant-1",
        "name": "Tenant 1",
        "is_active": True,
        "status": "active",
        "status_reason": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    tenant = await tenant_service.get_tenant_details(_FakeSession(row), tenant_id="tenant-1")

    assert tenant is not None
    assert tenant.id == "tenant-1"
    assert tenant.logo_file_key is None
