from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.deps import get_current_tenant_id
from app.core.security.rbac import require_permission
from app.db_deps import get_auth_db
from app.rbac.permissions import PERMISSION_BILLING_ACCESS, PERMISSION_REPORTING_READ
from app.accounting.schemas import FinancialStatementsReportOut
from app.reporting.schemas import (
    CompanyContactBreakdownOut,
    CompanyReportItemOut,
    CompanyReportsSnapshotOut,
    CompanyReportsSummaryOut,
    ContactCompanyBreakdownOut,
    ContactReportItemOut,
    ContactReportsSnapshotOut,
    ContactReportsSummaryOut,
    FinanceReportsSnapshotOut,
    PaymentStatusBreakdownOut,
    PaymentsSummaryOut,
    RevenueFlowReportOut,
    SupportCompanyBreakdownOut,
    SupportCountBreakdownOut,
    SupportReportItemOut,
    SupportReportsSnapshotOut,
    SupportReportsSummaryOut,
)
from app.reporting.service import (
    get_company_reports_snapshot,
    get_contact_reports_snapshot,
    get_finance_reports_snapshot,
    get_revenue_flow_report,
    get_support_reports_snapshot,
)

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get(
    "/probe",
    dependencies=[Depends(require_permission(PERMISSION_REPORTING_READ))],
)
async def reporting_probe() -> dict:
    return {
        "module": "reporting",
        "permission_required": PERMISSION_REPORTING_READ,
        "status": "ok",
    }


@router.get(
    "/revenue-flow",
    response_model=RevenueFlowReportOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def revenue_flow_report_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> RevenueFlowReportOut:
    report = await get_revenue_flow_report(db, tenant_id=tenant_id)
    return RevenueFlowReportOut(
        sales_summary=asdict(report.sales_report.summary),
        summary=asdict(report.summary),
        quote_status_breakdown=[asdict(item) for item in report.quote_status_breakdown],
        invoice_status_breakdown=[asdict(item) for item in report.invoice_status_breakdown],
    )


@router.get(
    "/finance",
    response_model=FinanceReportsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_BILLING_ACCESS))],
)
async def finance_reports_snapshot_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> FinanceReportsSnapshotOut:
    snapshot = await get_finance_reports_snapshot(db, tenant_id=tenant_id)
    return FinanceReportsSnapshotOut(
        revenue_flow=RevenueFlowReportOut(
            sales_summary=asdict(snapshot.revenue_flow.sales_report.summary),
            summary=asdict(snapshot.revenue_flow.summary),
            quote_status_breakdown=[asdict(item) for item in snapshot.revenue_flow.quote_status_breakdown],
            invoice_status_breakdown=[asdict(item) for item in snapshot.revenue_flow.invoice_status_breakdown],
        ),
        financial_statements=FinancialStatementsReportOut(**asdict(snapshot.financial_statements)),
        payments_summary=PaymentsSummaryOut(**asdict(snapshot.payments_summary)),
        payment_status_breakdown=[
            PaymentStatusBreakdownOut(**asdict(item)) for item in snapshot.payment_status_breakdown
        ],
    )


@router.get(
    "/contacts",
    response_model=ContactReportsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_REPORTING_READ))],
)
async def contact_reports_snapshot_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> ContactReportsSnapshotOut:
    snapshot = await get_contact_reports_snapshot(db, tenant_id=tenant_id)
    return ContactReportsSnapshotOut(
        summary=ContactReportsSummaryOut(**asdict(snapshot.summary)),
        contacts_by_company=[
            ContactCompanyBreakdownOut(**asdict(item)) for item in snapshot.contacts_by_company
        ],
        recent_contacts=[ContactReportItemOut(**asdict(item)) for item in snapshot.recent_contacts],
    )


@router.get(
    "/companies",
    response_model=CompanyReportsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_REPORTING_READ))],
)
async def company_reports_snapshot_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> CompanyReportsSnapshotOut:
    snapshot = await get_company_reports_snapshot(db, tenant_id=tenant_id)
    return CompanyReportsSnapshotOut(
        summary=CompanyReportsSummaryOut(**asdict(snapshot.summary)),
        contact_breakdown=[CompanyContactBreakdownOut(**asdict(item)) for item in snapshot.contact_breakdown],
        recent_companies=[CompanyReportItemOut(**asdict(item)) for item in snapshot.recent_companies],
    )


@router.get(
    "/support",
    response_model=SupportReportsSnapshotOut,
    dependencies=[Depends(require_permission(PERMISSION_REPORTING_READ))],
)
async def support_reports_snapshot_route(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_auth_db),
) -> SupportReportsSnapshotOut:
    snapshot = await get_support_reports_snapshot(db, tenant_id=tenant_id)
    return SupportReportsSnapshotOut(
        summary=SupportReportsSummaryOut(**asdict(snapshot.summary)),
        tickets_by_priority=[SupportCountBreakdownOut(**asdict(item)) for item in snapshot.tickets_by_priority],
        tickets_by_source=[SupportCountBreakdownOut(**asdict(item)) for item in snapshot.tickets_by_source],
        tickets_by_company=[SupportCompanyBreakdownOut(**asdict(item)) for item in snapshot.tickets_by_company],
        recent_tickets=[SupportReportItemOut(**asdict(item)) for item in snapshot.recent_tickets],
    )
