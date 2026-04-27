"use client";

import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { getApiErrorMessage } from "@/lib/api-errors";
import { createSupportTicket } from "@/services/support.service";
import {
    SUPPORT_TICKET_PRIORITIES,
    SUPPORT_TICKET_SOURCES,
    SUPPORT_TICKET_STATUSES,
    formatSupportLabel,
} from "@/lib/support";
import type { Company, Contact, Deal } from "@/types/crm";
import type { Invoice } from "@/types/finance";
import type { TenantUser } from "@/types/tenants";
import type {
    SupportTicket,
    SupportTicketCreateRequest,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
} from "@/types/support";

type SupportTicketFormMode = "create" | "edit";

type SupportTicketFormProps = {
    companies: Company[];
    contacts: Contact[];
    tenantUsers: TenantUser[];
    deals: Deal[];
    invoices: Invoice[];
    mode?: SupportTicketFormMode;
    initialValues?: Partial<SupportTicketCreateRequest>;
    onSubmit?: (payload: SupportTicketCreateRequest) => Promise<SupportTicket>;
    onSuccess?: (ticket: SupportTicket) => Promise<void> | void;
    title?: string;
    description?: string;
    submitLabel?: string;
    submittingLabel?: string;
    successMessage?: string;
};

const DEFAULT_FORM_STATE: SupportTicketCreateRequest = {
    title: "",
    description: "",
    status: "open",
    priority: "medium",
    source: "manual",
    company_id: null,
    contact_id: null,
    assigned_to_user_id: null,
    related_deal_id: null,
    related_invoice_id: null,
};

function buildInitialFormState(
    initialValues?: Partial<SupportTicketCreateRequest>,
): SupportTicketCreateRequest {
    return {
        ...DEFAULT_FORM_STATE,
        ...initialValues,
        title: initialValues?.title ?? DEFAULT_FORM_STATE.title,
        description: initialValues?.description ?? DEFAULT_FORM_STATE.description,
        status: initialValues?.status ?? DEFAULT_FORM_STATE.status,
        priority: initialValues?.priority ?? DEFAULT_FORM_STATE.priority,
        source: initialValues?.source ?? DEFAULT_FORM_STATE.source,
        company_id: initialValues?.company_id ?? DEFAULT_FORM_STATE.company_id,
        contact_id: initialValues?.contact_id ?? DEFAULT_FORM_STATE.contact_id,
        assigned_to_user_id:
            initialValues?.assigned_to_user_id ?? DEFAULT_FORM_STATE.assigned_to_user_id,
        related_deal_id: initialValues?.related_deal_id ?? DEFAULT_FORM_STATE.related_deal_id,
        related_invoice_id:
            initialValues?.related_invoice_id ?? DEFAULT_FORM_STATE.related_invoice_id,
    };
}

export default function SupportTicketForm({
    companies,
    contacts,
    tenantUsers,
    deals,
    invoices,
    mode = "create",
    initialValues,
    onSubmit,
    onSuccess,
    title,
    description,
    submitLabel,
    submittingLabel,
    successMessage,
}: SupportTicketFormProps) {
    const toast = useToast();
    const [formData, setFormData] = useState<SupportTicketCreateRequest>(() =>
        buildInitialFormState(initialValues),
    );
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [formSuccessMessage, setFormSuccessMessage] = useState<string>("");

    const resolvedOnSubmit = onSubmit ?? createSupportTicket;
    const resolvedTitle = title ?? (mode === "edit" ? "Update ticket" : "Create ticket");
    const resolvedDescription =
        description ??
        (mode === "edit"
            ? "Update the support record while keeping CRM and commercial links aligned."
            : "Create a real tenant-scoped support ticket linked back into your CRM where needed.");
    const resolvedSubmitLabel = submitLabel ?? (mode === "edit" ? "Save changes" : "Create ticket");
    const resolvedSubmittingLabel = submittingLabel ?? (mode === "edit" ? "Saving..." : "Creating...");
    const resolvedSuccessMessage =
        successMessage ?? (mode === "edit" ? "Ticket updated successfully." : "Ticket created successfully.");

    useEffect(() => {
        setFormData(buildInitialFormState(initialValues));
        setErrorMessage("");
        setFormSuccessMessage("");
    }, [initialValues]);

    const availableContacts = useMemo(() => {
        if (!formData.company_id) {
            return contacts;
        }

        return contacts.filter((contact) => contact.company_id === formData.company_id);
    }, [contacts, formData.company_id]);

    const availableDeals = useMemo(() => {
        if (!formData.company_id) {
            return deals;
        }

        return deals.filter((deal) => deal.company_id === formData.company_id);
    }, [deals, formData.company_id]);

    const availableInvoices = useMemo(() => {
        if (!formData.company_id) {
            return invoices;
        }

        return invoices.filter((invoice) => invoice.company_id === formData.company_id);
    }, [formData.company_id, invoices]);

    const activeTenantUsers = useMemo(() => {
        return tenantUsers.filter((user) => user.membership_is_active && user.user_is_active);
    }, [tenantUsers]);

    function updateField<K extends keyof SupportTicketCreateRequest>(
        field: K,
        value: SupportTicketCreateRequest[K],
    ): void {
        setFormData((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSubmitting(true);
            setErrorMessage("");
            setFormSuccessMessage("");

            const payload: SupportTicketCreateRequest = {
                title: formData.title.trim(),
                description: formData.description.trim(),
                status: formData.status,
                priority: formData.priority,
                source: formData.source,
                company_id: formData.company_id || null,
                contact_id: formData.contact_id || null,
                assigned_to_user_id: formData.assigned_to_user_id || null,
                related_deal_id: formData.related_deal_id || null,
                related_invoice_id: formData.related_invoice_id || null,
            };

            if (!payload.title) {
                setErrorMessage("Ticket title is required.");
                return;
            }

            if (!payload.description) {
                setErrorMessage("Ticket description is required.");
                return;
            }

            const savedTicket = await resolvedOnSubmit(payload);
            setFormSuccessMessage(resolvedSuccessMessage);
            toast.success(resolvedSuccessMessage);
            if (mode === "create") {
                setFormData(DEFAULT_FORM_STATE);
            }
            await onSuccess?.(savedTicket);
        } catch (error) {
            console.error("Failed to save support ticket:", error);
            const message = getApiErrorMessage(error, "The support ticket could not be saved.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    function renderSelectOptions<T extends { id: string }>(
        items: T[],
        getLabel: (item: T) => string,
    ) {
        return items.map((item) => (
            <option key={item.id} value={item.id}>
                {getLabel(item)}
            </option>
        ));
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">{resolvedTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">{resolvedDescription}</p>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="md:col-span-2">
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-title">
                            Ticket title
                        </label>
                        <input
                            id="support-ticket-title"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.title}
                            onChange={(event) => updateField("title", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-status">
                            Status
                        </label>
                        <select
                            id="support-ticket-status"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.status}
                            onChange={(event) =>
                                updateField("status", event.target.value as SupportTicketStatus)
                            }
                        >
                            {SUPPORT_TICKET_STATUSES.map((status) => (
                                <option key={status} value={status}>
                                    {formatSupportLabel(status)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-priority">
                            Priority
                        </label>
                        <select
                            id="support-ticket-priority"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.priority}
                            onChange={(event) =>
                                updateField("priority", event.target.value as SupportTicketPriority)
                            }
                        >
                            {SUPPORT_TICKET_PRIORITIES.map((priority) => (
                                <option key={priority} value={priority}>
                                    {formatSupportLabel(priority)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-source">
                            Source
                        </label>
                        <select
                            id="support-ticket-source"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.source}
                            onChange={(event) =>
                                updateField("source", event.target.value as SupportTicketSource)
                            }
                        >
                            {SUPPORT_TICKET_SOURCES.map((source) => (
                                <option key={source} value={source}>
                                    {formatSupportLabel(source)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-company">
                            Company
                        </label>
                        <select
                            id="support-ticket-company"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.company_id ?? ""}
                            onChange={(event) => {
                                const nextCompanyId = event.target.value || null;
                                updateField("company_id", nextCompanyId);
                                updateField("contact_id", null);
                                updateField("related_deal_id", null);
                                updateField("related_invoice_id", null);
                            }}
                        >
                            <option value="">No company</option>
                            {renderSelectOptions(companies, (company) => company.name)}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-contact">
                            Contact
                        </label>
                        <select
                            id="support-ticket-contact"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.contact_id ?? ""}
                            onChange={(event) => updateField("contact_id", event.target.value || null)}
                        >
                            <option value="">No contact</option>
                            {renderSelectOptions(
                                availableContacts,
                                (contact) =>
                                    [contact.first_name, contact.last_name].filter(Boolean).join(" "),
                            )}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-assigned-to">
                            Assigned to
                        </label>
                        <select
                            id="support-ticket-assigned-to"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.assigned_to_user_id ?? ""}
                            onChange={(event) =>
                                updateField("assigned_to_user_id", event.target.value || null)
                            }
                        >
                            <option value="">Unassigned</option>
                            {activeTenantUsers.map((user) => (
                                <option key={user.user_id} value={user.user_id}>
                                    {user.full_name?.trim() || user.email}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-deal">
                            Related deal
                        </label>
                        <select
                            id="support-ticket-deal"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.related_deal_id ?? ""}
                            onChange={(event) => updateField("related_deal_id", event.target.value || null)}
                        >
                            <option value="">No related deal</option>
                            {renderSelectOptions(availableDeals, (deal) => deal.name)}
                        </select>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-invoice">
                            Related invoice
                        </label>
                        <select
                            id="support-ticket-invoice"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.related_invoice_id ?? ""}
                            onChange={(event) => updateField("related_invoice_id", event.target.value || null)}
                        >
                            <option value="">No related invoice</option>
                            {renderSelectOptions(
                                availableInvoices,
                                (invoice) => `${invoice.number} (${invoice.status})`,
                            )}
                        </select>
                    </div>

                    <div className="md:col-span-2">
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="support-ticket-description">
                            Description
                        </label>
                        <textarea
                            id="support-ticket-description"
                            className="min-h-36 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.description}
                            onChange={(event) => updateField("description", event.target.value)}
                            required
                        />
                    </div>
                </div>

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                {formSuccessMessage ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                        {formSuccessMessage}
                    </div>
                ) : null}

                <div className="flex flex-wrap items-center justify-end gap-3">
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
                    </button>
                </div>
            </form>
        </section>
    );
}
