from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.security import deps as auth_deps
from app.core.security import rbac as security_rbac
from app.reporting import routes as reporting_routes
from app.reporting.service import (
    CompanyContactBreakdown,
    CompanyReportItem,
    CompanyReportsSnapshot,
    CompanyReportsSummary,
    ContactCompanyBreakdown,
    ContactReportItem,
    ContactReportsSnapshot,
    ContactReportsSummary,
    SupportCompanyBreakdown,
    SupportCountBreakdown,
    SupportReportItem,
    SupportReportsSnapshot,
    SupportReportsSummary,
)


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


async def _allow_permission(*args, **kwargs) -> bool:
    return True


def test_contact_reporting_route_returns_tenant_scoped_shape(monkeypatch) -> None:
    async def _noop_init_db() -> None:
        return None

    async def _fake_snapshot(*args, **kwargs) -> ContactReportsSnapshot:
        assert kwargs["tenant_id"] == "tenant-1"
        return ContactReportsSnapshot(
            summary=ContactReportsSummary(
                total_contacts=5,
                contacts_created_this_period_count=2,
                contacts_with_open_deals_count=1,
                contacts_with_won_deals_count=1,
                contacts_without_company_count=1,
                contacts_with_support_tickets_count=2,
                report_period_start=datetime(2026, 4, 1, tzinfo=UTC),
                report_period_end=datetime(2026, 5, 1, tzinfo=UTC),
                generated_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            ),
            contacts_by_company=[
                ContactCompanyBreakdown(company_id="company-1", company_name="Northwind", contact_count=3),
            ],
            recent_contacts=[
                ContactReportItem(
                    contact_id="contact-1",
                    full_name="Alicia Admin",
                    company_id="company-1",
                    company_name="Northwind",
                    email="alicia@example.com",
                    phone=None,
                    updated_at=datetime(2026, 4, 14, 8, 0, tzinfo=UTC),
                    open_deals_count=1,
                    won_deals_count=1,
                    support_ticket_count=1,
                )
            ],
        )

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(reporting_routes, "get_contact_reports_snapshot", _fake_snapshot)
    monkeypatch.setattr(security_rbac, "user_has_permission", _allow_permission)
    main_module.app.dependency_overrides[auth_deps.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[reporting_routes.get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/reporting/contacts",
                headers={"Authorization": "Bearer token", "X-Tenant-Id": "tenant-1"},
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["total_contacts"] == 5
    assert response.json()["contacts_by_company"][0]["company_name"] == "Northwind"
    assert response.json()["recent_contacts"][0]["full_name"] == "Alicia Admin"


def test_company_reporting_route_returns_tenant_scoped_shape(monkeypatch) -> None:
    async def _noop_init_db() -> None:
        return None

    async def _fake_snapshot(*args, **kwargs) -> CompanyReportsSnapshot:
        assert kwargs["tenant_id"] == "tenant-1"
        return CompanyReportsSnapshot(
            summary=CompanyReportsSummary(
                total_companies=2,
                companies_created_this_period_count=1,
                companies_with_open_deals_count=1,
                companies_with_won_deals_count=1,
                companies_with_contacts_count=1,
                companies_without_contacts_count=1,
                companies_with_invoices_count=1,
                companies_with_support_tickets_count=1,
                report_period_start=datetime(2026, 4, 1, tzinfo=UTC),
                report_period_end=datetime(2026, 5, 1, tzinfo=UTC),
                generated_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            ),
            contact_breakdown=[
                CompanyContactBreakdown(company_id="company-1", company_name="Northwind", contact_count=3),
            ],
            recent_companies=[
                CompanyReportItem(
                    company_id="company-1",
                    company_name="Northwind",
                    updated_at=datetime(2026, 4, 14, 8, 0, tzinfo=UTC),
                    contact_count=3,
                    open_deals_count=1,
                    won_deals_count=1,
                    invoice_count=1,
                    support_ticket_count=1,
                )
            ],
        )

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(reporting_routes, "get_company_reports_snapshot", _fake_snapshot)
    monkeypatch.setattr(security_rbac, "user_has_permission", _allow_permission)
    main_module.app.dependency_overrides[auth_deps.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[reporting_routes.get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/reporting/companies",
                headers={"Authorization": "Bearer token", "X-Tenant-Id": "tenant-1"},
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["total_companies"] == 2
    assert response.json()["contact_breakdown"][0]["contact_count"] == 3
    assert response.json()["recent_companies"][0]["invoice_count"] == 1


def test_support_reporting_route_returns_tenant_scoped_shape(monkeypatch) -> None:
    async def _noop_init_db() -> None:
        return None

    async def _fake_snapshot(*args, **kwargs) -> SupportReportsSnapshot:
        assert kwargs["tenant_id"] == "tenant-1"
        return SupportReportsSnapshot(
            summary=SupportReportsSummary(
                total_tickets=4,
                open_tickets=1,
                in_progress_tickets=1,
                waiting_on_customer_tickets=1,
                resolved_tickets=1,
                closed_tickets=0,
                urgent_active_tickets=1,
                tickets_linked_to_deals_count=1,
                tickets_linked_to_invoices_count=1,
                report_period_start=datetime(2026, 4, 1, tzinfo=UTC),
                report_period_end=datetime(2026, 5, 1, tzinfo=UTC),
                generated_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            ),
            tickets_by_priority=[SupportCountBreakdown(label="urgent", count=1)],
            tickets_by_source=[SupportCountBreakdown(label="email", count=2)],
            tickets_by_company=[
                SupportCompanyBreakdown(company_id="company-1", company_name="Northwind", ticket_count=3)
            ],
            recent_tickets=[
                SupportReportItem(
                    ticket_id="ticket-1",
                    title="Invoice correction",
                    status="open",
                    priority="urgent",
                    source="email",
                    company_id="company-1",
                    company_name="Northwind",
                    contact_id="contact-1",
                    related_deal_id="deal-1",
                    related_invoice_id="invoice-1",
                    updated_at=datetime(2026, 4, 14, 8, 0, tzinfo=UTC),
                )
            ],
        )

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    monkeypatch.setattr(reporting_routes, "get_support_reports_snapshot", _fake_snapshot)
    monkeypatch.setattr(security_rbac, "user_has_permission", _allow_permission)
    main_module.app.dependency_overrides[auth_deps.get_current_principal] = _override_principal
    main_module.app.dependency_overrides[reporting_routes.get_auth_db] = _override_auth_db

    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/reporting/support",
                headers={"Authorization": "Bearer token", "X-Tenant-Id": "tenant-1"},
            )
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["total_tickets"] == 4
    assert response.json()["tickets_by_priority"][0]["label"] == "urgent"
    assert response.json()["recent_tickets"][0]["ticket_id"] == "ticket-1"
