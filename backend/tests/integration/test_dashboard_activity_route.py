from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import main as main_module
from app.audit import routes as audit_routes
from app.audit.service import RecentAuditActivity
from app.core.security import deps as auth_deps


def test_recent_audit_activity_route_returns_tenant_scoped_items(monkeypatch) -> None:
    async def _noop_init_db() -> None:
        return None

    async def _override_principal() -> dict[str, object]:
        return {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "roles": ["owner"],
            "tenant_status": "active",
            "tenant_is_active": True,
            "user_is_active": True,
            "membership_is_active": True,
        }

    async def _override_auth_db():
        yield object()

    async def _fake_recent_activity(*args, **kwargs) -> list[RecentAuditActivity]:
        assert kwargs["tenant_id"] == "tenant-1"
        assert kwargs["limit"] == 2
        return [
            RecentAuditActivity(
                id="audit-1",
                action="sales.deal.create",
                resource="deal",
                resource_id="deal-1",
                status_code=200,
                message="Created deal Acceptance Deal",
                actor_user_id="user-1",
                actor_full_name="Alex Admin",
                actor_email="alex@example.com",
                created_at=datetime(2026, 4, 13, 12, 0, tzinfo=UTC),
            ),
            RecentAuditActivity(
                id="audit-2",
                action="payments.invoice.record",
                resource="invoice_payment",
                resource_id="payment-1",
                status_code=201,
                message="Recorded invoice payment",
                actor_user_id="user-1",
                actor_full_name="Alex Admin",
                actor_email="alex@example.com",
                created_at=datetime(2026, 4, 13, 11, 30, tzinfo=UTC),
            ),
        ]

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(audit_routes, "list_recent_activity", _fake_recent_activity)

    main_module.app.dependency_overrides[auth_deps.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[audit_routes.get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/audit/recent?limit=2",
                headers={
                    "Authorization": "Bearer token",
                    "X-Tenant-Id": "tenant-1",
                },
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "audit-1",
                "action": "sales.deal.create",
                "resource": "deal",
                "resource_id": "deal-1",
                "status_code": 200,
                "message": "Created deal Acceptance Deal",
                "actor_user_id": "user-1",
                "actor_full_name": "Alex Admin",
                "actor_email": "alex@example.com",
                "created_at": "2026-04-13T12:00:00Z",
            },
            {
                "id": "audit-2",
                "action": "payments.invoice.record",
                "resource": "invoice_payment",
                "resource_id": "payment-1",
                "status_code": 201,
                "message": "Recorded invoice payment",
                "actor_user_id": "user-1",
                "actor_full_name": "Alex Admin",
                "actor_email": "alex@example.com",
                "created_at": "2026-04-13T11:30:00Z",
            },
        ],
        "total": 2,
    }
