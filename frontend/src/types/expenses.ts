export type ExpenseStatus = "draft" | "submitted" | "approved" | "paid";

export interface Expense {
    id: string;
    tenant_id: string;
    title: string;
    description: string | null;
    amount: string;
    currency: string;
    expense_date: string;
    category: string;
    status: ExpenseStatus;
    vendor_name: string | null;
    created_at: string;
    updated_at: string;
}

export interface ExpensesListResponse {
    items: Expense[];
    total: number;
}

export interface ExpenseCreateRequest {
    title: string;
    description: string | null;
    amount: number;
    currency: string;
    expense_date: string;
    category: string;
    status: ExpenseStatus;
    vendor_name: string | null;
}

export interface ExpenseUpdateRequest {
    title?: string | null;
    description?: string | null;
    amount?: number | null;
    currency?: string | null;
    expense_date?: string | null;
    category?: string | null;
    status?: ExpenseStatus | null;
    vendor_name?: string | null;
}
