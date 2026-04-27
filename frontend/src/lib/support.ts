import type {
    SupportTicket,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
} from "@/types/support";

export const SUPPORT_TICKET_STATUSES: SupportTicketStatus[] = [
    "open",
    "in progress",
    "waiting on customer",
    "resolved",
    "closed",
];

export const SUPPORT_TICKET_PRIORITIES: SupportTicketPriority[] = [
    "low",
    "medium",
    "high",
    "urgent",
];

export const SUPPORT_TICKET_SOURCES: SupportTicketSource[] = [
    "manual",
    "email",
    "whatsapp",
    "phone",
    "web",
];

export function formatSupportLabel(value: string): string {
    return value
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export function getSupportStatusClasses(status: SupportTicketStatus): string {
    switch (status) {
        case "open":
            return "border-sky-200 bg-sky-50 text-sky-700";
        case "in progress":
            return "border-amber-200 bg-amber-50 text-amber-800";
        case "waiting on customer":
            return "border-violet-200 bg-violet-50 text-violet-700";
        case "resolved":
            return "border-emerald-200 bg-emerald-50 text-emerald-700";
        case "closed":
            return "border-slate-200 bg-slate-100 text-slate-700";
    }
}

export function getSupportPriorityClasses(priority: SupportTicketPriority): string {
    switch (priority) {
        case "low":
            return "border-slate-200 bg-slate-100 text-slate-700";
        case "medium":
            return "border-sky-200 bg-sky-50 text-sky-700";
        case "high":
            return "border-amber-200 bg-amber-50 text-amber-800";
        case "urgent":
            return "border-red-200 bg-red-50 text-red-700";
    }
}

export function formatSupportTimestamp(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

export function buildSupportTicketUpdatePayload(
    ticket: SupportTicket,
): {
    title: string;
    description: string;
    status: SupportTicketStatus;
    priority: SupportTicketPriority;
    source: SupportTicketSource;
    company_id: string | null;
    contact_id: string | null;
    assigned_to_user_id: string | null;
    related_deal_id: string | null;
    related_invoice_id: string | null;
} {
    return {
        title: ticket.title,
        description: ticket.description,
        status: ticket.status,
        priority: ticket.priority,
        source: ticket.source,
        company_id: ticket.company_id,
        contact_id: ticket.contact_id,
        assigned_to_user_id: ticket.assigned_to_user_id,
        related_deal_id: ticket.related_deal_id,
        related_invoice_id: ticket.related_invoice_id,
    };
}
