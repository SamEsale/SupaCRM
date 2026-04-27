from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.accounting.schemas import FinancialStatementsReportOut
from app.sales.schemas import SalesForecastSummaryOut


class RevenueStatusBreakdownOut(BaseModel):
    status: str
    count: int
    total_amount: Decimal
    currencies: list[str]


class RevenueFlowSummaryOut(BaseModel):
    quote_count: int
    quote_created_this_period_count: int
    invoice_count: int
    invoice_created_this_period_count: int
    invoice_issued_count: int
    invoice_paid_count: int
    invoice_overdue_count: int
    quote_currencies: list[str]
    invoice_currencies: list[str]
    generated_at: datetime
    report_period_start: datetime
    report_period_end: datetime


class RevenueFlowReportOut(BaseModel):
    sales_summary: SalesForecastSummaryOut
    summary: RevenueFlowSummaryOut
    quote_status_breakdown: list[RevenueStatusBreakdownOut]
    invoice_status_breakdown: list[RevenueStatusBreakdownOut]


class PaymentStatusBreakdownOut(BaseModel):
    status: str
    count: int
    total_amount: Decimal
    currencies: list[str]


class PaymentsSummaryOut(BaseModel):
    payment_count: int
    completed_payment_count: int
    completed_payment_amount: Decimal
    pending_payment_count: int
    failed_payment_count: int
    cancelled_payment_count: int
    payment_currencies: list[str]
    generated_at: datetime


class FinanceReportsSnapshotOut(BaseModel):
    revenue_flow: RevenueFlowReportOut
    financial_statements: FinancialStatementsReportOut
    payments_summary: PaymentsSummaryOut
    payment_status_breakdown: list[PaymentStatusBreakdownOut]


class ContactReportsSummaryOut(BaseModel):
    total_contacts: int
    contacts_created_this_period_count: int
    contacts_with_open_deals_count: int
    contacts_with_won_deals_count: int
    contacts_without_company_count: int
    contacts_with_support_tickets_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


class ContactCompanyBreakdownOut(BaseModel):
    company_id: str | None = None
    company_name: str
    contact_count: int


class ContactReportItemOut(BaseModel):
    contact_id: str
    full_name: str
    company_id: str | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    updated_at: datetime
    open_deals_count: int
    won_deals_count: int
    support_ticket_count: int


class ContactReportsSnapshotOut(BaseModel):
    summary: ContactReportsSummaryOut
    contacts_by_company: list[ContactCompanyBreakdownOut]
    recent_contacts: list[ContactReportItemOut]


class CompanyReportsSummaryOut(BaseModel):
    total_companies: int
    companies_created_this_period_count: int
    companies_with_open_deals_count: int
    companies_with_won_deals_count: int
    companies_with_contacts_count: int
    companies_without_contacts_count: int
    companies_with_invoices_count: int
    companies_with_support_tickets_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


class CompanyContactBreakdownOut(BaseModel):
    company_id: str
    company_name: str
    contact_count: int


class CompanyReportItemOut(BaseModel):
    company_id: str
    company_name: str
    updated_at: datetime
    contact_count: int
    open_deals_count: int
    won_deals_count: int
    invoice_count: int
    support_ticket_count: int


class CompanyReportsSnapshotOut(BaseModel):
    summary: CompanyReportsSummaryOut
    contact_breakdown: list[CompanyContactBreakdownOut]
    recent_companies: list[CompanyReportItemOut]


class SupportReportsSummaryOut(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    waiting_on_customer_tickets: int
    resolved_tickets: int
    closed_tickets: int
    urgent_active_tickets: int
    tickets_linked_to_deals_count: int
    tickets_linked_to_invoices_count: int
    report_period_start: datetime
    report_period_end: datetime
    generated_at: datetime


class SupportCountBreakdownOut(BaseModel):
    label: str
    count: int


class SupportCompanyBreakdownOut(BaseModel):
    company_id: str | None = None
    company_name: str
    ticket_count: int


class SupportReportItemOut(BaseModel):
    ticket_id: str
    title: str
    status: str
    priority: str
    source: str
    company_id: str | None = None
    company_name: str | None = None
    contact_id: str | None = None
    related_deal_id: str | None = None
    related_invoice_id: str | None = None
    updated_at: datetime


class SupportReportsSnapshotOut(BaseModel):
    summary: SupportReportsSummaryOut
    tickets_by_priority: list[SupportCountBreakdownOut]
    tickets_by_source: list[SupportCountBreakdownOut]
    tickets_by_company: list[SupportCompanyBreakdownOut]
    recent_tickets: list[SupportReportItemOut]
