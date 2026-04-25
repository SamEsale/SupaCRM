import { apiClient } from "@/lib/api-client";
import type { FinancialStatementsReport } from "@/types/accounting";
import type { RevenueFlowReport } from "@/types/finance";
import type { PaymentsSummary, PaymentStatusBreakdown } from "@/types/payments";
import type {
    CompanyReportsSnapshot,
    ContactReportsSnapshot,
    SupportReportsSnapshot,
} from "@/types/reporting";

export async function getRevenueFlowReport(): Promise<RevenueFlowReport> {
    const response = await apiClient.get<RevenueFlowReport>("/reporting/revenue-flow");
    return response.data;
}

export interface FinanceReportsSnapshot {
    revenue_flow: RevenueFlowReport;
    financial_statements: FinancialStatementsReport;
    payments_summary: PaymentsSummary;
    payment_status_breakdown: PaymentStatusBreakdown[];
}

export async function getFinanceReportsSnapshot(): Promise<FinanceReportsSnapshot> {
    const response = await apiClient.get<FinanceReportsSnapshot>("/reporting/finance");
    return response.data;
}

export async function getContactReportsSnapshot(): Promise<ContactReportsSnapshot> {
    const response = await apiClient.get<ContactReportsSnapshot>("/reporting/contacts");
    return response.data;
}

export async function getCompanyReportsSnapshot(): Promise<CompanyReportsSnapshot> {
    const response = await apiClient.get<CompanyReportsSnapshot>("/reporting/companies");
    return response.data;
}

export async function getSupportReportsSnapshot(): Promise<SupportReportsSnapshot> {
    const response = await apiClient.get<SupportReportsSnapshot>("/reporting/support");
    return response.data;
}
