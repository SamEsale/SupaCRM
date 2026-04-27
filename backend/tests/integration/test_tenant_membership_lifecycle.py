from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.tenants import service as tenant_service


class _FakeResult:
    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> None:
        return None

    def scalar_one_or_none(self) -> None:
        return None


class _TrackingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(
        self,
        statement: Any,
        params: dict[str, Any] | None = None,
    ) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        self.calls.append((sql, params or {}))
        return _FakeResult()


def _member(
    *,
    user_id: str,
    email: str,
    full_name: str | None = None,
    user_is_active: bool = True,
    membership_is_active: bool = True,
    is_owner: bool = False,
    role_names: list[str] | None = None,
) -> tenant_service.TenantUserSummary:
    return tenant_service.TenantUserSummary(
        user_id=user_id,
        email=email,
        full_name=full_name,
        user_is_active=user_is_active,
        membership_is_active=membership_is_active,
        is_owner=is_owner,
        role_names=list(role_names or []),
        membership_created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_update_tenant_membership_deactivates_member_and_invalidates_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _TrackingSession()
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        ),
        _member(
            user_id="user-2",
            email="member@example.com",
            role_names=["user"],
        ),
    ]
    invalidated: list[str] = []

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)
    monkeypatch.setattr(
        tenant_service.auth_cache,
        "invalidate_snapshots_for_tenant",
        _fake_invalidate,
    )

    result = await tenant_service.update_tenant_membership(
        session,
        tenant_id="tenant-1",
        user_id="user-2",
        membership_is_active=False,
    )

    assert result.membership_is_active is False
    assert result.is_owner is False
    assert invalidated == ["tenant-1"]
    assert any(
        "update public.tenant_users set is_active = :is_active" in sql
        and params["user_id"] == "user-2"
        and params["is_active"] is False
        for sql, params in session.calls
    )


@pytest.mark.asyncio
async def test_update_tenant_membership_reactivates_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _TrackingSession()
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        ),
        _member(
            user_id="user-2",
            email="member@example.com",
            membership_is_active=False,
            role_names=["user"],
        ),
    ]

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    async def _fake_invalidate(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)
    monkeypatch.setattr(
        tenant_service.auth_cache,
        "invalidate_snapshots_for_tenant",
        _fake_invalidate,
    )

    result = await tenant_service.update_tenant_membership(
        session,
        tenant_id="tenant-1",
        user_id="user-2",
        membership_is_active=True,
    )

    assert result.membership_is_active is True
    assert any(
        "update public.tenant_users set is_active = :is_active" in sql
        and params["is_active"] is True
        for sql, params in session.calls
    )


@pytest.mark.asyncio
async def test_remove_tenant_membership_deletes_roles_and_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _TrackingSession()
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        ),
        _member(
            user_id="user-2",
            email="member@example.com",
            role_names=["user"],
        ),
    ]

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    async def _fake_invalidate(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)
    monkeypatch.setattr(
        tenant_service.auth_cache,
        "invalidate_snapshots_for_tenant",
        _fake_invalidate,
    )

    result = await tenant_service.remove_tenant_membership(
        session,
        tenant_id="tenant-1",
        user_id="user-2",
    )

    assert result.removed is True
    assert any(
        "delete from public.tenant_user_roles" in sql and params["user_id"] == "user-2"
        for sql, params in session.calls
    )
    assert any(
        "delete from public.tenant_users" in sql and params["user_id"] == "user-2"
        for sql, params in session.calls
    )


@pytest.mark.asyncio
async def test_update_tenant_membership_rejects_deactivating_last_active_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        )
    ]

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)

    with pytest.raises(ValueError, match="Cannot deactivate the last active owner"):
        await tenant_service.update_tenant_membership(
            _TrackingSession(),
            tenant_id="tenant-1",
            user_id="owner-1",
            membership_is_active=False,
        )


@pytest.mark.asyncio
async def test_remove_tenant_membership_rejects_removing_last_active_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        )
    ]

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)

    with pytest.raises(ValueError, match="Cannot remove the last active owner"):
        await tenant_service.remove_tenant_membership(
            _TrackingSession(),
            tenant_id="tenant-1",
            user_id="owner-1",
        )


@pytest.mark.asyncio
async def test_update_tenant_membership_rejects_orphaning_tenant_admin_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    users = [
        _member(
            user_id="admin-1",
            email="admin@example.com",
            role_names=["admin"],
        ),
        _member(
            user_id="user-2",
            email="member@example.com",
            role_names=["user"],
        ),
    ]

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)

    with pytest.raises(ValueError, match="Cannot orphan tenant admin access"):
        await tenant_service.update_tenant_membership(
            _TrackingSession(),
            tenant_id="tenant-1",
            user_id="admin-1",
            membership_is_active=False,
        )


@pytest.mark.asyncio
async def test_update_tenant_membership_transfers_ownership_and_realigns_owner_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _TrackingSession()
    users = [
        _member(
            user_id="owner-1",
            email="owner@example.com",
            is_owner=True,
            role_names=["owner", "admin"],
        ),
        _member(
            user_id="admin-2",
            email="admin@example.com",
            role_names=["admin"],
        ),
    ]
    granted_roles: list[tuple[str, str]] = []
    removed_roles: list[tuple[str, str]] = []
    invalidated: list[str] = []

    async def _fake_list_tenant_users(*_: object, **__: object):
        return users

    async def _fake_ensure_role_assignment_by_name(
        _session: object,
        *,
        tenant_id: str,
        user_id: str,
        role_name: str,
    ) -> SimpleNamespace:
        granted_roles.append((user_id, role_name))
        return SimpleNamespace(role_name=role_name, role_id=f"role-{role_name}", created_assignment=True)

    async def _fake_remove_role_assignment_by_name(
        _session: object,
        *,
        tenant_id: str,
        user_id: str,
        role_name: str,
    ) -> None:
        removed_roles.append((user_id, role_name))

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(tenant_service, "list_tenant_users", _fake_list_tenant_users)
    monkeypatch.setattr(
        tenant_service,
        "_ensure_role_assignment_by_name",
        _fake_ensure_role_assignment_by_name,
    )
    monkeypatch.setattr(
        tenant_service,
        "_remove_role_assignment_by_name",
        _fake_remove_role_assignment_by_name,
    )
    monkeypatch.setattr(
        tenant_service.auth_cache,
        "invalidate_snapshots_for_tenant",
        _fake_invalidate,
    )

    result = await tenant_service.update_tenant_membership(
        session,
        tenant_id="tenant-1",
        user_id="admin-2",
        is_owner=True,
        transfer_owner_from_user_id="owner-1",
    )

    assert result.is_owner is True
    assert result.transferred_owner_from_user_id == "owner-1"
    assert granted_roles == [("admin-2", "owner")]
    assert removed_roles == [("owner-1", "owner")]
    assert invalidated == ["tenant-1"]
    assert any(
        "update public.tenant_users set is_owner = :is_owner" in sql
        and params["user_id"] == "admin-2"
        and params["is_owner"] is True
        for sql, params in session.calls
    )
    assert any(
        "update public.tenant_users set is_owner = :is_owner" in sql
        and params["user_id"] == "owner-1"
        and params["is_owner"] is False
        for sql, params in session.calls
    )
