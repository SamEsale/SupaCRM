from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


AccountingAccountType = Literal["asset", "liability", "equity", "revenue", "expense"]


class AccountingAccountCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    account_type: AccountingAccountType
    is_active: bool = True


class AccountingAccountOut(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    account_type: AccountingAccountType
    system_key: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountingAccountListResponse(BaseModel):
    items: list[AccountingAccountOut]
    total: int


class JournalEntryLineOut(BaseModel):
    id: str
    tenant_id: str
    journal_entry_id: str
    account_id: str
    account_code: str
    account_name: str
    account_type: AccountingAccountType
    line_order: int
    description: str | None = None
    debit_amount: Decimal
    credit_amount: Decimal
    created_at: datetime


class JournalEntryOut(BaseModel):
    id: str
    tenant_id: str
    entry_date: date
    memo: str
    source_type: str | None = None
    source_id: str | None = None
    source_event: str | None = None
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    created_at: datetime
    lines: list[JournalEntryLineOut]


class JournalEntryListResponse(BaseModel):
    items: list[JournalEntryOut]
    total: int


class FinancialStatementLineOut(BaseModel):
    account_id: str
    code: str
    name: str
    account_type: AccountingAccountType
    total_amount: Decimal
    currencies: list[str]


class ProfitAndLossStatementOut(BaseModel):
    revenue_lines: list[FinancialStatementLineOut]
    expense_lines: list[FinancialStatementLineOut]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal
    currencies: list[str]


class BalanceSheetStatementOut(BaseModel):
    asset_lines: list[FinancialStatementLineOut]
    liability_lines: list[FinancialStatementLineOut]
    equity_lines: list[FinancialStatementLineOut]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    currencies: list[str]


class ReceivablesInvoiceItemOut(BaseModel):
    invoice_id: str
    invoice_number: str
    company_id: str
    status: str
    due_date: date
    currency: str
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal


class ReceivablesSummaryOut(BaseModel):
    open_receivables_amount: Decimal
    issued_invoice_count: int
    overdue_invoice_count: int
    paid_invoice_count: int
    currencies: list[str]
    items: list[ReceivablesInvoiceItemOut]


class FinancialStatementsReportOut(BaseModel):
    profit_and_loss: ProfitAndLossStatementOut
    balance_sheet: BalanceSheetStatementOut
    receivables: ReceivablesSummaryOut
    vat_supported: bool
    vat_note: str
    generated_at: datetime
