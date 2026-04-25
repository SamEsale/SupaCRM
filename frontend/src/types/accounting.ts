export type AccountingAccountType =
    | "asset"
    | "liability"
    | "equity"
    | "revenue"
    | "expense";

export interface AccountingAccount {
    id: string;
    tenant_id: string;
    code: string;
    name: string;
    account_type: AccountingAccountType;
    system_key: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface AccountingAccountListResponse {
    items: AccountingAccount[];
    total: number;
}

export interface JournalEntryLine {
    id: string;
    tenant_id: string;
    journal_entry_id: string;
    account_id: string;
    account_code: string;
    account_name: string;
    account_type: AccountingAccountType;
    line_order: number;
    description: string | null;
    debit_amount: string;
    credit_amount: string;
    created_at: string;
}

export interface JournalEntry {
    id: string;
    tenant_id: string;
    entry_date: string;
    memo: string;
    source_type: string | null;
    source_id: string | null;
    source_event: string | null;
    currency: string;
    total_debit: string;
    total_credit: string;
    created_at: string;
    lines: JournalEntryLine[];
}

export interface JournalEntryListResponse {
    items: JournalEntry[];
    total: number;
}

export interface FinancialStatementLine {
    account_id: string;
    code: string;
    name: string;
    account_type: AccountingAccountType;
    total_amount: string;
    currencies: string[];
}

export interface ProfitAndLossStatement {
    revenue_lines: FinancialStatementLine[];
    expense_lines: FinancialStatementLine[];
    total_revenue: string;
    total_expenses: string;
    net_income: string;
    currencies: string[];
}

export interface BalanceSheetStatement {
    asset_lines: FinancialStatementLine[];
    liability_lines: FinancialStatementLine[];
    equity_lines: FinancialStatementLine[];
    total_assets: string;
    total_liabilities: string;
    total_equity: string;
    total_liabilities_and_equity: string;
    currencies: string[];
}

export interface ReceivablesInvoiceItem {
    invoice_id: string;
    invoice_number: string;
    company_id: string;
    status: string;
    due_date: string;
    currency: string;
    total_amount: string;
    paid_amount: string;
    outstanding_amount: string;
}

export interface ReceivablesSummary {
    open_receivables_amount: string;
    issued_invoice_count: number;
    overdue_invoice_count: number;
    paid_invoice_count: number;
    currencies: string[];
    items: ReceivablesInvoiceItem[];
}

export interface FinancialStatementsReport {
    profit_and_loss: ProfitAndLossStatement;
    balance_sheet: BalanceSheetStatement;
    receivables: ReceivablesSummary;
    vat_supported: boolean;
    vat_note: string;
    generated_at: string;
}
