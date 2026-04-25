import { apiClient } from "@/lib/api-client";
import type {
    Expense,
    ExpenseCreateRequest,
    ExpensesListResponse,
    ExpenseStatus,
    ExpenseUpdateRequest,
} from "@/types/expenses";

export interface ExpensesListParams {
    status?: ExpenseStatus;
    category?: string;
    limit?: number;
    offset?: number;
}

export async function getExpenses(params: ExpensesListParams = {}): Promise<ExpensesListResponse> {
    const response = await apiClient.get<ExpensesListResponse>("/expenses", {
        params: {
            status: params.status,
            category: params.category,
            limit: params.limit,
            offset: params.offset,
        },
    });
    return response.data;
}

export async function getExpenseById(expenseId: string): Promise<Expense> {
    const response = await apiClient.get<Expense>(`/expenses/${expenseId}`);
    return response.data;
}

export async function createExpense(payload: ExpenseCreateRequest): Promise<Expense> {
    const response = await apiClient.post<Expense>("/expenses", payload);
    return response.data;
}

export async function updateExpense(expenseId: string, payload: ExpenseUpdateRequest): Promise<Expense> {
    const response = await apiClient.patch<Expense>(`/expenses/${expenseId}`, payload);
    return response.data;
}
