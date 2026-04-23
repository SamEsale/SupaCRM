"use client";

import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useToast } from "@/components/feedback/ToastProvider";
import {
    parseStrictDecimalAmountInput,
    sanitizeStrictDecimalInput,
    shouldBlockStrictDecimalKey,
    TOTAL_AMOUNT_INVALID_MESSAGE,
} from "@/components/finance/amount-utils";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import { getMarketingCampaigns, createWhatsAppLeadIntake } from "@/services/marketing.service";
import type { Company, Contact } from "@/types/crm";
import type { MarketingCampaign, WhatsAppLeadIntakeRequest } from "@/types/marketing";

type WhatsAppLeadIntakeFormState = WhatsAppLeadIntakeRequest;

const DEFAULT_FORM_STATE: WhatsAppLeadIntakeFormState = {
    sender_name: null,
    sender_phone: "",
    message_text: "",
    message_type: "text",
    received_at: null,
    company_id: null,
    company_name: null,
    contact_id: null,
    email: null,
    amount: "0",
    currency: "USD",
    campaign_id: null,
    notes: null,
    whatsapp_account_id: null,
};

function isNotFoundError(error: unknown): boolean {
    if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof error.response === "object" &&
        error.response !== null &&
        "status" in error.response &&
        error.response.status === 404
    ) {
        return true;
    }

    return axios.isAxiosError(error) && error.response?.status === 404;
}

export default function WhatsAppLeadIntakeForm() {
    const auth = useAuth();
    const router = useRouter();
    const toast = useToast();
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [campaigns, setCampaigns] = useState<MarketingCampaign[]>([]);
    const [formState, setFormState] = useState<WhatsAppLeadIntakeFormState>(DEFAULT_FORM_STATE);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [campaignLoadWarning, setCampaignLoadWarning] = useState<string>("");
    const [amountError, setAmountError] = useState<string>("");

    const availableContacts = useMemo(() => {
        if (!formState.company_id) {
            return contacts;
        }
        return contacts.filter((contact) => contact.company_id === formState.company_id);
    }, [contacts, formState.company_id]);

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function load(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                setCampaignLoadWarning("");

                const [companiesResponse, contactsResponse] = await Promise.all([
                    getCompanies(),
                    getContacts(),
                ]);

                let campaignsResponse: { items?: MarketingCampaign[] } = { items: [] };
                try {
                    campaignsResponse = await getMarketingCampaigns({ channel: "whatsapp" });
                } catch (error) {
                    console.warn("WhatsApp campaign enrichment could not be loaded:", error);

                    if (isMounted) {
                        if (isNotFoundError(error)) {
                            setCampaignLoadWarning(
                                "WhatsApp campaign drafts are currently unavailable, but you can still capture and convert the lead.",
                            );
                        } else {
                            setCampaignLoadWarning(
                                "WhatsApp campaign context could not be loaded right now. You can still continue with intake.",
                            );
                        }
                    }
                }

                if (!isMounted) {
                    return;
                }

                setCompanies(companiesResponse.items ?? []);
                setContacts(contactsResponse.items ?? []);
                setCampaigns(campaignsResponse.items ?? []);
            } catch (error) {
                console.error("Failed to load WhatsApp intake data:", error);
                if (isMounted) {
                    setErrorMessage("The WhatsApp intake workspace could not be loaded from the backend.");
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void load();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    useEffect(() => {
        if (!formState.contact_id) {
            return;
        }

        const selectedContact = contacts.find((contact) => contact.id === formState.contact_id);
        if (!selectedContact) {
            return;
        }

        setFormState((current) => ({
            ...current,
            company_id: current.company_id || selectedContact.company_id || null,
            sender_name:
                current.sender_name ||
                [selectedContact.first_name, selectedContact.last_name].filter(Boolean).join(" ") ||
                null,
            sender_phone: current.sender_phone || selectedContact.phone || "",
            email: current.email || selectedContact.email || null,
        }));
    }, [contacts, formState.contact_id]);

    function updateField<K extends keyof WhatsAppLeadIntakeFormState>(
        field: K,
        value: WhatsAppLeadIntakeFormState[K],
    ): void {
        setFormState((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSubmitting(true);
            setErrorMessage("");

            const amountResult = parseStrictDecimalAmountInput(formState.amount);
            if (amountResult.error || amountResult.value === null) {
                setAmountError(amountResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE);
                return;
            }

            if (
                !formState.company_id &&
                !formState.company_name?.trim() &&
                !formState.contact_id
            ) {
                setErrorMessage("Select a company, choose a contact with a company, or enter a new company name.");
                return;
            }

            const payload: WhatsAppLeadIntakeRequest = {
                sender_name: formState.sender_name?.trim() || null,
                sender_phone: formState.sender_phone.trim(),
                message_text: formState.message_text.trim(),
                message_type: formState.message_type?.trim() || "text",
                received_at: formState.received_at || null,
                company_id: formState.company_id || null,
                company_name: formState.company_name?.trim() || null,
                contact_id: formState.contact_id || null,
                email: formState.email?.trim() || null,
                amount: String(amountResult.value),
                currency: formState.currency.trim().toUpperCase(),
                campaign_id: formState.campaign_id || null,
                notes: formState.notes?.trim() || null,
                whatsapp_account_id: formState.whatsapp_account_id?.trim() || null,
            };

            const result = await createWhatsAppLeadIntake(payload);
            setFormState(DEFAULT_FORM_STATE);
            toast.success("WhatsApp lead intake saved.");
            router.push(`/deals/${result.deal.id}?createdFrom=whatsapp-intake`);
            router.refresh();
        } catch (error) {
            console.error("Failed to save WhatsApp intake:", error);
            const message = getApiErrorMessage(error, "The WhatsApp lead intake could not be saved.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">WhatsApp lead intake</h2>
            <p className="mt-2 text-sm text-slate-600">
                Capture inbound WhatsApp context manually, attach CRM context where possible, and create a deal-backed lead on the live sales flow.
            </p>
            <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                This page stores WhatsApp context honestly without claiming webhook or provider connectivity.
            </div>
            {campaignLoadWarning ? (
                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {campaignLoadWarning}
                </div>
            ) : null}

            {isLoading ? (
                <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    Loading companies, contacts, and WhatsApp campaign context.
                </div>
            ) : (
                <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                    <div className="grid gap-4 md:grid-cols-2">
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-sender-name">
                                Contact name
                            </label>
                            <input
                                id="wa-sender-name"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.sender_name ?? ""}
                                onChange={(event) => updateField("sender_name", event.target.value || null)}
                                placeholder="Alicia Andersson"
                            />
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-sender-phone">
                                Phone
                            </label>
                            <input
                                id="wa-sender-phone"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.sender_phone}
                                onChange={(event) => updateField("sender_phone", event.target.value)}
                                placeholder="+46 555 010 101"
                                required
                            />
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-email">
                                Email
                            </label>
                            <input
                                id="wa-email"
                                type="email"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.email ?? ""}
                                onChange={(event) => updateField("email", event.target.value || null)}
                                placeholder="lead@company.com"
                            />
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-received-at">
                                Received at
                            </label>
                            <input
                                id="wa-received-at"
                                type="datetime-local"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.received_at ? formState.received_at.slice(0, 16) : ""}
                                onChange={(event) =>
                                    updateField(
                                        "received_at",
                                        event.target.value ? new Date(event.target.value).toISOString() : null,
                                    )
                                }
                            />
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-company">
                                Existing company
                            </label>
                            <select
                                id="wa-company"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.company_id ?? ""}
                                onChange={(event) => {
                                    updateField("company_id", event.target.value || null);
                                    updateField("contact_id", null);
                                }}
                            >
                                <option value="">Select company</option>
                                {companies.map((company) => (
                                    <option key={company.id} value={company.id}>
                                        {company.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-company-name">
                                Or new company name
                            </label>
                            <input
                                id="wa-company-name"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.company_name ?? ""}
                                onChange={(event) => updateField("company_name", event.target.value || null)}
                                placeholder="Northwind Labs"
                            />
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-contact">
                                Existing contact
                            </label>
                            <select
                                id="wa-contact"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.contact_id ?? ""}
                                onChange={(event) => updateField("contact_id", event.target.value || null)}
                            >
                                <option value="">Create or reuse by phone/email</option>
                                {availableContacts.map((contact) => (
                                    <option key={contact.id} value={contact.id}>
                                        {[contact.first_name, contact.last_name].filter(Boolean).join(" ")}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-campaign">
                                WhatsApp campaign
                            </label>
                            <select
                                id="wa-campaign"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.campaign_id ?? ""}
                                onChange={(event) => updateField("campaign_id", event.target.value || null)}
                            >
                                <option value="">No campaign</option>
                                {campaigns.map((campaign) => (
                                    <option key={campaign.id} value={campaign.id}>
                                        {campaign.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-amount">
                                Initial amount
                            </label>
                            <input
                                id="wa-amount"
                                type="text"
                                inputMode="decimal"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.amount}
                                onChange={(event) => {
                                    updateField("amount", sanitizeStrictDecimalInput(event.target.value));
                                    setAmountError("");
                                }}
                                onKeyDown={(event) => {
                                    if (shouldBlockStrictDecimalKey(event.key)) {
                                        event.preventDefault();
                                    }
                                }}
                            />
                            {amountError ? <p className="mt-1 text-sm text-red-600">{amountError}</p> : null}
                        </div>
                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-currency">
                                Currency
                            </label>
                            <input
                                id="wa-currency"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                                value={formState.currency}
                                onChange={(event) => updateField("currency", event.target.value)}
                                maxLength={3}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-message">
                            Message content
                        </label>
                        <textarea
                            id="wa-message"
                            className="min-h-36 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formState.message_text}
                            onChange={(event) => updateField("message_text", event.target.value)}
                            placeholder="Paste or summarize the inbound WhatsApp message."
                            required
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="wa-notes">
                            Qualification notes
                        </label>
                        <textarea
                            id="wa-notes"
                            className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formState.notes ?? ""}
                            onChange={(event) => updateField("notes", event.target.value || null)}
                            placeholder="Add extra qualification context, urgency, or next-step notes."
                        />
                    </div>

                    {errorMessage ? (
                        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                            {errorMessage}
                        </div>
                    ) : null}

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Creating lead..." : "Create WhatsApp lead"}
                    </button>
                </form>
            )}
        </section>
    );
}
