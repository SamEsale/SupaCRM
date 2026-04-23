"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/feedback/ToastProvider";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-errors";
import { triggerBrowserDownload } from "@/lib/download-file";
import { getCompanies } from "@/services/companies.service";
import { getContacts } from "@/services/contacts.service";
import {
    createMarketingCampaign,
    createMarketingExecutionFollowUpHandoff,
    exportMarketingCampaignAudiencePreviewCsv,
    exportMarketingCampaignExecutionResultsCsv,
    getMarketingCampaignAudiencePreview,
    getMarketingCampaignDetail,
    getMarketingCampaignExecutionDetail,
    getMarketingCampaigns,
    startMarketingCampaignEmailSend,
    updateMarketingCampaign,
} from "@/services/marketing.service";
import type { Company, Contact } from "@/types/crm";
import type {
    MarketingAudiencePreviewExclusionCount,
    MarketingAudienceRecipientEligibilityStatus,
    MarketingCampaign,
    MarketingCampaignAudiencePreview,
    MarketingCampaignAudienceType,
    MarketingCampaignDetail,
    MarketingCampaignExecution,
    MarketingCampaignExecutionDetail,
    MarketingCampaignEditableStatus,
    MarketingCampaignExecutionRecipient,
    MarketingExecutionFollowUpHandoffResult,
    MarketingExecutionRecipientResultFilter,
    MarketingCampaignUpsertRequest,
} from "@/types/marketing";

const AUDIENCE_PREVIEW_SAMPLE_LIMIT = 25;
const ACTIVE_EXECUTION_POLL_INTERVAL_MS = 3000;

type CampaignFormState = MarketingCampaignUpsertRequest;

const DEFAULT_FORM_STATE: CampaignFormState = {
    name: "",
    channel: "email",
    audience_type: "all_contacts",
    audience_description: null,
    target_company_id: null,
    target_contact_id: null,
    subject: "",
    message_body: "",
    status: "draft",
    scheduled_for: null,
};

function formatLabel(value: string): string {
    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function formatAudienceType(value: MarketingCampaignAudienceType): string {
    return {
        all_contacts: "All contacts",
        target_company_contacts: "Company contacts",
        target_contact_only: "Single contact",
    }[value];
}

function buildContactLabel(contact: Contact): string {
    return (
        [contact.first_name, contact.last_name].filter(Boolean).join(" ").trim() ||
        contact.email ||
        contact.phone ||
        contact.id
    );
}

function buildExecutionRecipientLabel(recipient: MarketingCampaignExecutionRecipient): string {
    return recipient.contact_name || recipient.email;
}

function toDateTimeLocal(value: string | null): string {
    if (!value) {
        return "";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "";
    }

    const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

function formatDateTime(value: string | null): string {
    if (!value) {
        return "Not recorded";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString();
}

function toEditableStatus(status: MarketingCampaign["status"]): MarketingCampaignEditableStatus {
    return status === "scheduled" ? "scheduled" : "draft";
}

function buildFormState(campaign?: MarketingCampaign | null): CampaignFormState {
    if (!campaign) {
        return { ...DEFAULT_FORM_STATE };
    }

    return {
        name: campaign.name,
        channel: campaign.channel,
        audience_type: campaign.audience_type,
        audience_description: campaign.audience_description,
        target_company_id: campaign.target_company_id,
        target_contact_id: campaign.target_contact_id,
        subject: campaign.subject,
        message_body: campaign.message_body,
        status: toEditableStatus(campaign.status),
        scheduled_for: campaign.scheduled_for,
    };
}

function resolveCampaignTargetLabel(
    campaign: MarketingCampaign,
    companies: Company[],
    contacts: Contact[],
): string {
    if (campaign.audience_type === "all_contacts") {
        return "All tenant contacts";
    }

    if (campaign.audience_type === "target_company_contacts") {
        return (
            companies.find((company) => company.id === campaign.target_company_id)?.name ||
            "Selected company"
        );
    }

    const contact = contacts.find((item) => item.id === campaign.target_contact_id);
    return contact ? buildContactLabel(contact) : "Selected contact";
}

function getEligibilityBadgeClasses(
    status: MarketingAudienceRecipientEligibilityStatus,
): string {
    if (status === "eligible") {
        return "bg-emerald-100 text-emerald-700";
    }
    if (status === "duplicate_contact_method") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-red-100 text-red-700";
}

function getExecutionStatusBadgeClasses(status: string): string {
    if (status === "sent" || status === "completed") {
        return "bg-emerald-100 text-emerald-700";
    }
    if (status === "pending" || status === "queued" || status === "sending") {
        return "bg-slate-100 text-slate-700";
    }
    if (status === "blocked") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-red-100 text-red-700";
}

function getFeedbackClasses(tone: "success" | "error" | "info"): string {
    if (tone === "error") {
        return "border-red-200 bg-red-50 text-red-700";
    }
    if (tone === "success") {
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
    }
    return "border-slate-200 bg-slate-50 text-slate-700";
}

function renderExclusionChips(exclusionCounts: MarketingAudiencePreviewExclusionCount[]) {
    if (exclusionCounts.length === 0) {
        return <p className="text-sm text-slate-600">No exclusion reasons in the current snapshot.</p>;
    }

    return (
        <div className="mt-3 flex flex-wrap gap-2">
            {exclusionCounts.map((item) => (
                <span
                    key={item.reason}
                    className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                >
                    {formatLabel(item.reason)}: {item.count}
                </span>
            ))}
        </div>
    );
}

function getDefaultExecutionRecipientFilter(
    execution: MarketingCampaignExecution | null | undefined,
): MarketingExecutionRecipientResultFilter {
    if (execution?.failed_recipients) {
        return "failed";
    }
    return "all";
}

function getExecutionRecipientFilterCount(
    detail: MarketingCampaignExecutionDetail | null,
    status: MarketingExecutionRecipientResultFilter,
): number {
    return detail?.recipient_counts.find((item) => item.status === status)?.count ?? 0;
}

function formatExecutionLabel(executionId: string): string {
    if (executionId.length <= 18) {
        return executionId;
    }
    return `${executionId.slice(0, 8)}...${executionId.slice(-6)}`;
}

function formatHandoffStatus(value: string | null): string {
    if (!value) {
        return "Not handed off";
    }
    return formatLabel(value);
}

export default function MarketingCampaignsManager() {
    const auth = useAuth();
    const toast = useToast();
    const [campaigns, setCampaigns] = useState<MarketingCampaign[]>([]);
    const [companies, setCompanies] = useState<Company[]>([]);
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
    const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
    const [selectedRecipientFilter, setSelectedRecipientFilter] =
        useState<MarketingExecutionRecipientResultFilter>("all");
    const [formState, setFormState] = useState<CampaignFormState>(DEFAULT_FORM_STATE);
    const [campaignDetail, setCampaignDetail] = useState<MarketingCampaignDetail | null>(null);
    const [executionDetail, setExecutionDetail] = useState<MarketingCampaignExecutionDetail | null>(null);
    const [audiencePreview, setAudiencePreview] = useState<MarketingCampaignAudiencePreview | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
    const [isExecutionDetailLoading, setIsExecutionDetailLoading] = useState<boolean>(false);
    const [isPreviewLoading, setIsPreviewLoading] = useState<boolean>(false);
    const [isExportingPreview, setIsExportingPreview] = useState<boolean>(false);
    const [isExportingExecutionResults, setIsExportingExecutionResults] = useState<boolean>(false);
    const [isStartingSend, setIsStartingSend] = useState<boolean>(false);
    const [isConfirmationOpen, setIsConfirmationOpen] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [detailErrorMessage, setDetailErrorMessage] = useState<string>("");
    const [executionDetailErrorMessage, setExecutionDetailErrorMessage] = useState<string>("");
    const [previewErrorMessage, setPreviewErrorMessage] = useState<string>("");
    const [previewFeedbackMessage, setPreviewFeedbackMessage] = useState<string>("");
    const [previewFeedbackTone, setPreviewFeedbackTone] = useState<"success" | "error" | "info">("info");
    const [executionFeedbackMessage, setExecutionFeedbackMessage] = useState<string>("");
    const [executionFeedbackTone, setExecutionFeedbackTone] =
        useState<"success" | "error" | "info">("info");
    const [selectedFailedRecipientIds, setSelectedFailedRecipientIds] = useState<string[]>([]);
    const [isFollowUpConfirmationOpen, setIsFollowUpConfirmationOpen] = useState<boolean>(false);
    const [isSubmittingFollowUpHandoff, setIsSubmittingFollowUpHandoff] = useState<boolean>(false);

    const selectedCampaign = useMemo(
        () => campaigns.find((campaign) => campaign.id === selectedCampaignId) ?? null,
        [campaigns, selectedCampaignId],
    );
    const availableContacts = useMemo(() => {
        if (!formState.target_company_id) {
            return contacts;
        }

        return contacts.filter((contact) => contact.company_id === formState.target_company_id);
    }, [contacts, formState.target_company_id]);

    const emailReadyContacts = useMemo(() => {
        return contacts.filter((contact) => Boolean(contact.email?.trim())).length;
    }, [contacts]);

    const sendBlockers = audiencePreview?.send_readiness.blocked_reasons ?? [];
    const latestExecutionStatus = campaignDetail?.latest_execution?.status ?? null;
    const hasActiveExecution =
        latestExecutionStatus === "queued" || latestExecutionStatus === "sending";
    const canStartSend =
        Boolean(selectedCampaignId) &&
        selectedCampaign?.channel === "email" &&
        Boolean(audiencePreview) &&
        Boolean(audiencePreview?.send_readiness.can_send);
    const visibleFailedRecipients = useMemo(() => {
        return executionDetail?.recipients.filter((recipient) => recipient.status === "failed") ?? [];
    }, [executionDetail]);
    const selectedVisibleFailedRecipients = useMemo(() => {
        const selectedSet = new Set(selectedFailedRecipientIds);
        return visibleFailedRecipients.filter((recipient) => selectedSet.has(recipient.id));
    }, [selectedFailedRecipientIds, visibleFailedRecipients]);
    const allVisibleFailedRecipientsSelected =
        visibleFailedRecipients.length > 0 &&
        selectedVisibleFailedRecipients.length === visibleFailedRecipients.length;

    function upsertCampaign(savedCampaign: MarketingCampaign): void {
        setCampaigns((current) => {
            const existingIndex = current.findIndex((item) => item.id === savedCampaign.id);
            if (existingIndex === -1) {
                return [savedCampaign, ...current];
            }

            const next = [...current];
            next[existingIndex] = savedCampaign;
            return next;
        });
    }

    async function loadCampaignWorkspace(): Promise<void> {
        const [campaignsResponse, companiesResponse, contactsResponse] = await Promise.all([
            getMarketingCampaigns(),
            getCompanies(),
            getContacts(),
        ]);

        setCampaigns(campaignsResponse.items ?? []);
        setCompanies(companiesResponse.items ?? []);
        setContacts(contactsResponse.items ?? []);
    }

    async function loadSelectedCampaignPreview(campaignId: string): Promise<void> {
        try {
            setIsPreviewLoading(true);
            setPreviewErrorMessage("");
            const preview = await getMarketingCampaignAudiencePreview(campaignId, {
                sample_limit: AUDIENCE_PREVIEW_SAMPLE_LIMIT,
            });
            setAudiencePreview(preview);
        } catch (error) {
            console.error("Failed to load marketing audience preview:", error);
            setAudiencePreview(null);
            setPreviewErrorMessage(
                getApiErrorMessage(error, "The campaign audience preview could not be loaded."),
            );
        } finally {
            setIsPreviewLoading(false);
        }
    }

    async function loadSelectedCampaignDetail(campaignId: string): Promise<void> {
        try {
            setIsDetailLoading(true);
            setDetailErrorMessage("");
            const detail = await getMarketingCampaignDetail(campaignId);
            setCampaignDetail(detail);
            upsertCampaign(detail.campaign);
        } catch (error) {
            console.error("Failed to load marketing campaign detail:", error);
            setDetailErrorMessage(
                getApiErrorMessage(error, "The latest execution status could not be loaded."),
            );
        } finally {
            setIsDetailLoading(false);
        }
    }

    async function loadSelectedExecutionDetail(
        campaignId: string,
        executionId: string,
        recipientFilter: MarketingExecutionRecipientResultFilter,
    ): Promise<void> {
        try {
            setIsExecutionDetailLoading(true);
            setExecutionDetailErrorMessage("");
            const detail = await getMarketingCampaignExecutionDetail(campaignId, executionId, {
                recipient_status: recipientFilter,
            });
            setExecutionDetail(detail);
        } catch (error) {
            console.error("Failed to load marketing execution detail:", error);
            setExecutionDetail(null);
            setExecutionDetailErrorMessage(
                getApiErrorMessage(error, "The selected execution results could not be loaded."),
            );
        } finally {
            setIsExecutionDetailLoading(false);
        }
    }

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
                await loadCampaignWorkspace();
            } catch (error) {
                console.error("Failed to load marketing campaigns:", error);
                if (isMounted) {
                    setErrorMessage("The campaign workspace could not be loaded from the backend.");
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
        setFormState(buildFormState(selectedCampaign));
        setErrorMessage("");
        setSuccessMessage("");
        setIsConfirmationOpen(false);
    }, [selectedCampaign]);

    useEffect(() => {
        setSelectedExecutionId(null);
        setSelectedRecipientFilter("all");
        setExecutionDetail(null);
        setExecutionDetailErrorMessage("");
        setExecutionFeedbackMessage("");
        setSelectedFailedRecipientIds([]);
        setIsFollowUpConfirmationOpen(false);
    }, [selectedCampaignId]);

    useEffect(() => {
        const visibleFailedIds = new Set(visibleFailedRecipients.map((recipient) => recipient.id));
        setSelectedFailedRecipientIds((current) => current.filter((recipientId) => visibleFailedIds.has(recipientId)));
        setIsFollowUpConfirmationOpen(false);
    }, [visibleFailedRecipients]);

    useEffect(() => {
        if (!auth.isReady || !auth.isAuthenticated || !auth.accessToken || !selectedCampaignId) {
            setCampaignDetail(null);
            setExecutionDetail(null);
            setAudiencePreview(null);
            setDetailErrorMessage("");
            setExecutionDetailErrorMessage("");
            setPreviewErrorMessage("");
            setIsDetailLoading(false);
            setIsExecutionDetailLoading(false);
            setIsPreviewLoading(false);
            return;
        }

        const campaignId = selectedCampaignId;
        void Promise.all([
            loadSelectedCampaignDetail(campaignId),
            loadSelectedCampaignPreview(campaignId),
        ]);
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, selectedCampaignId]);

    useEffect(() => {
        const executionHistory = campaignDetail?.execution_history ?? [];
        if (executionHistory.length === 0) {
            setSelectedExecutionId(null);
            setExecutionDetail(null);
            return;
        }

        if (
            selectedExecutionId &&
            executionHistory.some((execution) => execution.id === selectedExecutionId)
        ) {
            return;
        }

        const nextExecution = executionHistory[0];
        setSelectedExecutionId(nextExecution.id);
        setSelectedRecipientFilter(getDefaultExecutionRecipientFilter(nextExecution));
    }, [campaignDetail, selectedExecutionId]);

    useEffect(() => {
        if (
            !auth.isReady ||
            !auth.isAuthenticated ||
            !auth.accessToken ||
            !selectedCampaignId ||
            !selectedExecutionId
        ) {
            return;
        }

        void loadSelectedExecutionDetail(
            selectedCampaignId,
            selectedExecutionId,
            selectedRecipientFilter,
        );
    }, [
        auth.accessToken,
        auth.isAuthenticated,
        auth.isReady,
        selectedCampaignId,
        selectedExecutionId,
        selectedRecipientFilter,
    ]);

    useEffect(() => {
        if (
            !auth.isReady ||
            !auth.isAuthenticated ||
            !auth.accessToken ||
            !selectedCampaignId ||
            !hasActiveExecution
        ) {
            return;
        }

        const campaignId = selectedCampaignId;
        const latestExecutionId = campaignDetail?.latest_execution?.id ?? null;
        const intervalId = window.setInterval(() => {
            void loadSelectedCampaignDetail(campaignId);
            if (selectedExecutionId && selectedExecutionId === latestExecutionId) {
                void loadSelectedExecutionDetail(
                    campaignId,
                    selectedExecutionId,
                    selectedRecipientFilter,
                );
            }
        }, ACTIVE_EXECUTION_POLL_INTERVAL_MS);

        return () => {
            window.clearInterval(intervalId);
        };
    }, [
        auth.accessToken,
        auth.isAuthenticated,
        auth.isReady,
        campaignDetail?.latest_execution?.id,
        hasActiveExecution,
        selectedCampaignId,
        selectedExecutionId,
        selectedRecipientFilter,
    ]);

    function updateField<K extends keyof CampaignFormState>(
        field: K,
        value: CampaignFormState[K],
    ): void {
        setFormState((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function handleAudienceTypeChange(audienceType: MarketingCampaignAudienceType): void {
        setFormState((current) => {
            if (audienceType === "all_contacts") {
                return {
                    ...current,
                    audience_type: audienceType,
                    target_company_id: null,
                    target_contact_id: null,
                };
            }

            if (audienceType === "target_company_contacts") {
                return {
                    ...current,
                    audience_type: audienceType,
                    target_contact_id: null,
                };
            }

            return {
                ...current,
                audience_type: audienceType,
            };
        });
    }

    function handleCreateNew(): void {
        setSelectedCampaignId(null);
        setSelectedExecutionId(null);
        setCampaignDetail(null);
        setExecutionDetail(null);
        setAudiencePreview(null);
        setFormState({ ...DEFAULT_FORM_STATE });
        setErrorMessage("");
        setSuccessMessage("");
        setDetailErrorMessage("");
        setExecutionDetailErrorMessage("");
        setPreviewErrorMessage("");
        setPreviewFeedbackMessage("");
        setExecutionFeedbackMessage("");
        setIsConfirmationOpen(false);
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSaving(true);
            setErrorMessage("");
            setSuccessMessage("");

            if (formState.channel === "email" && !formState.subject?.trim()) {
                setErrorMessage("Email campaigns require a subject.");
                return;
            }

            if (formState.status === "scheduled" && !formState.scheduled_for) {
                setErrorMessage("Scheduled campaigns require a scheduled time.");
                return;
            }

            if (
                formState.audience_type === "target_company_contacts" &&
                !formState.target_company_id
            ) {
                setErrorMessage("Company audiences require a target company.");
                return;
            }

            if (
                formState.audience_type === "target_contact_only" &&
                !formState.target_contact_id
            ) {
                setErrorMessage("Single-contact audiences require a target contact.");
                return;
            }

            const payload: MarketingCampaignUpsertRequest = {
                name: formState.name.trim(),
                channel: formState.channel,
                audience_type: formState.audience_type,
                audience_description: formState.audience_description?.trim() || null,
                target_company_id:
                    formState.audience_type === "all_contacts"
                        ? null
                        : formState.target_company_id || null,
                target_contact_id:
                    formState.audience_type === "target_contact_only"
                        ? formState.target_contact_id || null
                        : null,
                subject:
                    formState.channel === "email" ? formState.subject?.trim() || null : null,
                message_body: formState.message_body.trim(),
                status: formState.status,
                scheduled_for: formState.status === "scheduled" ? formState.scheduled_for : null,
            };

            const saved = selectedCampaignId
                ? await updateMarketingCampaign(selectedCampaignId, payload)
                : await createMarketingCampaign(payload);

            upsertCampaign(saved);
            setSelectedCampaignId(saved.id);
            setFormState(buildFormState(saved));
            const message = selectedCampaignId ? "Campaign updated." : "Campaign draft created.";
            setSuccessMessage(message);
            toast.success(message);
        } catch (error) {
            console.error("Failed to save campaign:", error);
            const message = getApiErrorMessage(error, "The campaign could not be saved.");
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSaving(false);
        }
    }

    async function handleExportAudiencePreview(): Promise<void> {
        if (!selectedCampaignId) {
            setPreviewFeedbackTone("error");
            setPreviewFeedbackMessage("Save or select a campaign before exporting its audience preview.");
            return;
        }

        try {
            setIsExportingPreview(true);
            setPreviewFeedbackMessage("");

            const download = await exportMarketingCampaignAudiencePreviewCsv(selectedCampaignId);
            triggerBrowserDownload(download.blob, download.filename);

            const message = `Exported ${download.rowCount} recipient${download.rowCount === 1 ? "" : "s"} to ${download.filename}.`;
            setPreviewFeedbackTone("success");
            setPreviewFeedbackMessage(message);
            toast.success(message);
        } catch (error) {
            const message = getApiErrorMessage(
                error,
                "The campaign audience preview export could not be generated.",
            );
            setPreviewFeedbackTone("error");
            setPreviewFeedbackMessage(message);
            toast.error(message);
        } finally {
            setIsExportingPreview(false);
        }
    }

    async function handleConfirmSend(): Promise<void> {
        if (!selectedCampaignId) {
            return;
        }

        try {
            setIsStartingSend(true);
            setPreviewFeedbackMessage("");
            const detail = await startMarketingCampaignEmailSend(selectedCampaignId);
            setCampaignDetail(detail);
            upsertCampaign(detail.campaign);
            const nextExecution = detail.latest_execution ?? detail.execution_history[0] ?? null;
            if (nextExecution) {
                setSelectedExecutionId(nextExecution.id);
                setSelectedRecipientFilter(getDefaultExecutionRecipientFilter(nextExecution));
            }
            setIsConfirmationOpen(false);
            const message = "Campaign send queued with a frozen audience snapshot.";
            setPreviewFeedbackTone("success");
            setPreviewFeedbackMessage(message);
            toast.success(message);
            await loadSelectedCampaignPreview(selectedCampaignId);
        } catch (error) {
            const message = getApiErrorMessage(
                error,
                "The campaign send could not be started.",
            );
            setPreviewFeedbackTone("error");
            setPreviewFeedbackMessage(message);
            toast.error(message);
        } finally {
            setIsStartingSend(false);
        }
    }

    const previewFeedbackClasses = getFeedbackClasses(previewFeedbackTone);
    const executionFeedbackClasses = getFeedbackClasses(executionFeedbackTone);

    function toggleFailedRecipientSelection(recipientId: string): void {
        setSelectedFailedRecipientIds((current) =>
            current.includes(recipientId)
                ? current.filter((id) => id !== recipientId)
                : [...current, recipientId],
        );
    }

    function toggleSelectAllVisibleFailedRecipients(): void {
        if (allVisibleFailedRecipientsSelected) {
            setSelectedFailedRecipientIds([]);
            return;
        }
        setSelectedFailedRecipientIds(visibleFailedRecipients.map((recipient) => recipient.id));
    }

    async function handleExportExecutionResults(): Promise<void> {
        if (!selectedCampaignId || !selectedExecutionId) {
            setExecutionFeedbackTone("error");
            setExecutionFeedbackMessage("Select an execution before exporting recipient results.");
            return;
        }

        try {
            setIsExportingExecutionResults(true);
            setExecutionFeedbackMessage("");
            const download = await exportMarketingCampaignExecutionResultsCsv(
                selectedCampaignId,
                selectedExecutionId,
                { recipient_status: selectedRecipientFilter },
            );
            triggerBrowserDownload(download.blob, download.filename);

            const message = `Exported ${download.rowCount} execution result${download.rowCount === 1 ? "" : "s"} to ${download.filename}.`;
            setExecutionFeedbackTone("success");
            setExecutionFeedbackMessage(message);
            toast.success(message);
        } catch (error) {
            const message = getApiErrorMessage(
                error,
                "The selected execution results export could not be generated.",
            );
            setExecutionFeedbackTone("error");
            setExecutionFeedbackMessage(message);
            toast.error(message);
        } finally {
            setIsExportingExecutionResults(false);
        }
    }

    async function handleConfirmFollowUpHandoff(): Promise<void> {
        if (!selectedCampaignId || !selectedExecutionId || selectedFailedRecipientIds.length === 0) {
            setExecutionFeedbackTone("error");
            setExecutionFeedbackMessage("Select failed recipients before creating follow-up tasks.");
            return;
        }

        try {
            setIsSubmittingFollowUpHandoff(true);
            setExecutionFeedbackMessage("");
            const response = await createMarketingExecutionFollowUpHandoff(
                selectedCampaignId,
                selectedExecutionId,
                {
                    recipient_ids: selectedFailedRecipientIds,
                    priority: "high",
                },
            );

            const failureMessages = response.results
                .filter((result) => result.status === "failed")
                .map((result: MarketingExecutionFollowUpHandoffResult) => {
                    const detail = result.message
                        ? `: ${result.message === "already_handed_off" ? "already_handed_off" : result.message}`
                        : "";
                    return `${result.contact_name || result.email || result.recipient_id}${detail}`;
                });
            const message =
                response.failed_count === 0
                    ? `Created ${response.created_count} follow-up task${response.created_count === 1 ? "" : "s"} from failed recipients.`
                    : `Created ${response.created_count} follow-up task${response.created_count === 1 ? "" : "s"}; ${response.failed_count} handoff${response.failed_count === 1 ? "" : "s"} failed. ${failureMessages.join(" | ")}`;

            setExecutionFeedbackTone(response.failed_count === 0 ? "success" : "error");
            setExecutionFeedbackMessage(message);
            if (response.failed_count === 0) {
                toast.success(message);
            } else {
                toast.error(message);
            }
            setSelectedFailedRecipientIds([]);
            setIsFollowUpConfirmationOpen(false);
        } catch (error) {
            const message = getApiErrorMessage(
                error,
                "The follow-up handoff could not be created from the selected failed recipients.",
            );
            setExecutionFeedbackTone("error");
            setExecutionFeedbackMessage(message);
            toast.error(message);
        } finally {
            setIsSubmittingFollowUpHandoff(false);
        }
    }

    return (
        <div className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-semibold text-slate-900">Audience preparation</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Campaign audiences stay grounded in tenant CRM contacts. Imported contact and lead CSVs feed this workspace, while send confirmation now freezes a separate execution snapshot at start time.
                        </p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">
                        {emailReadyContacts} contact{emailReadyContacts === 1 ? "" : "s"} currently have an email address.
                    </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                    <Link
                        href="/contacts"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Prepare contact CSVs
                    </Link>
                    <Link
                        href="/deals"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Prepare lead CSVs
                    </Link>
                </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.05fr_1.3fr]">
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-xl font-semibold text-slate-900">Campaign drafts</h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Store campaign content and audience scope against the real tenant contact base.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={handleCreateNew}
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                        >
                            New draft
                        </button>
                    </div>

                    {isLoading ? (
                        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                            Loading campaigns from the backend.
                        </div>
                    ) : campaigns.length === 0 ? (
                        <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                            No campaigns have been saved for this tenant yet.
                        </div>
                    ) : (
                        <div className="mt-6 space-y-3">
                            {campaigns.map((campaign) => (
                                <button
                                    key={campaign.id}
                                    type="button"
                                    onClick={() => setSelectedCampaignId(campaign.id)}
                                    className={`w-full rounded-xl border px-4 py-4 text-left transition ${
                                        campaign.id === selectedCampaignId
                                            ? "border-slate-900 bg-slate-50"
                                            : "border-slate-200 hover:border-slate-300"
                                    }`}
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-semibold text-slate-900">{campaign.name}</p>
                                        <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                                            <span className="rounded-full bg-slate-100 px-2 py-1">
                                                {formatLabel(campaign.channel)}
                                            </span>
                                            <span className="rounded-full bg-slate-100 px-2 py-1">
                                                {formatAudienceType(campaign.audience_type)}
                                            </span>
                                            <span className="rounded-full bg-slate-100 px-2 py-1">
                                                {formatLabel(campaign.status)}
                                            </span>
                                        </div>
                                    </div>
                                    <p className="mt-2 text-sm text-slate-600">
                                        {campaign.audience_description || "No audience description yet."}
                                    </p>
                                    <p className="mt-2 text-xs text-slate-500">
                                        Target: {resolveCampaignTargetLabel(campaign, companies, contacts)}
                                    </p>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">
                        {selectedCampaign ? "Edit campaign" : "Create campaign"}
                    </h2>
                    <p className="mt-1 text-sm text-slate-600">
                        Audience scope is explicit in this slice so operators can preview, confirm, and freeze a send snapshot against real campaign data.
                    </p>

                    <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-name">
                                    Campaign name
                                </label>
                                <input
                                    id="campaign-name"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={formState.name}
                                    onChange={(event) => updateField("name", event.target.value)}
                                    required
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-channel">
                                    Channel
                                </label>
                                <select
                                    id="campaign-channel"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={formState.channel}
                                    onChange={(event) =>
                                        updateField("channel", event.target.value as CampaignFormState["channel"])
                                    }
                                >
                                    <option value="email">Email</option>
                                    <option value="whatsapp">WhatsApp</option>
                                </select>
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-audience-type">
                                    Audience scope
                                </label>
                                <select
                                    id="campaign-audience-type"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={formState.audience_type}
                                    onChange={(event) =>
                                        handleAudienceTypeChange(
                                            event.target.value as MarketingCampaignAudienceType,
                                        )
                                    }
                                >
                                    <option value="all_contacts">All contacts</option>
                                    <option value="target_company_contacts">Company contacts</option>
                                    <option value="target_contact_only">Single contact</option>
                                </select>
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-status">
                                    Status
                                </label>
                                <select
                                    id="campaign-status"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={formState.status}
                                    onChange={(event) =>
                                        updateField(
                                            "status",
                                            event.target.value as MarketingCampaignEditableStatus,
                                        )
                                    }
                                >
                                    <option value="draft">Draft</option>
                                    <option value="scheduled">Scheduled</option>
                                </select>
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-company">
                                    Target company
                                </label>
                                <select
                                    id="campaign-company"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                                    value={formState.target_company_id ?? ""}
                                    disabled={formState.audience_type === "all_contacts"}
                                    onChange={(event) => {
                                        updateField("target_company_id", event.target.value || null);
                                        if (formState.audience_type !== "target_contact_only") {
                                            updateField("target_contact_id", null);
                                        }
                                    }}
                                >
                                    <option value="">
                                        {formState.audience_type === "all_contacts"
                                            ? "Not used for all contacts"
                                            : "No company target"}
                                    </option>
                                    {companies.map((company) => (
                                        <option key={company.id} value={company.id}>
                                            {company.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-contact">
                                    Target contact
                                </label>
                                <select
                                    id="campaign-contact"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                                    value={formState.target_contact_id ?? ""}
                                    disabled={formState.audience_type !== "target_contact_only"}
                                    onChange={(event) => updateField("target_contact_id", event.target.value || null)}
                                >
                                    <option value="">
                                        {formState.audience_type === "target_contact_only"
                                            ? "Select one contact"
                                            : "Only used for single-contact audiences"}
                                    </option>
                                    {availableContacts.map((contact) => (
                                        <option key={contact.id} value={contact.id}>
                                            {buildContactLabel(contact)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-scheduled">
                                    Scheduled for
                                </label>
                                <input
                                    id="campaign-scheduled"
                                    type="datetime-local"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={toDateTimeLocal(formState.scheduled_for)}
                                    onChange={(event) =>
                                        updateField(
                                            "scheduled_for",
                                            event.target.value
                                                ? new Date(event.target.value).toISOString()
                                                : null,
                                        )
                                    }
                                />
                            </div>
                        </div>

                        {formState.channel === "email" ? (
                            <div>
                                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-subject">
                                    Subject
                                </label>
                                <input
                                    id="campaign-subject"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                    value={formState.subject ?? ""}
                                    onChange={(event) => updateField("subject", event.target.value)}
                                    placeholder="Spring launch follow-up"
                                />
                            </div>
                        ) : null}

                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-audience">
                                Audience or segment description
                            </label>
                            <input
                                id="campaign-audience"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.audience_description ?? ""}
                                onChange={(event) => updateField("audience_description", event.target.value)}
                                placeholder="Qualified Nordic leads needing a follow-up quote."
                            />
                        </div>

                        <div>
                            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="campaign-body">
                                Message body
                            </label>
                            <textarea
                                id="campaign-body"
                                className="min-h-40 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                                value={formState.message_body}
                                onChange={(event) => updateField("message_body", event.target.value)}
                                placeholder="Write the core launch-scope campaign content here."
                                required
                            />
                        </div>

                        {errorMessage ? (
                            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {errorMessage}
                            </div>
                        ) : null}
                        {successMessage ? (
                            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                                {successMessage}
                            </div>
                        ) : null}

                        <button
                            type="submit"
                            disabled={isLoading || isSaving}
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isSaving ? "Saving..." : selectedCampaign ? "Update campaign" : "Create campaign"}
                        </button>
                    </form>
                </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-semibold text-slate-900">Audience preview</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Preview current tenant eligibility before export or send confirmation.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <button
                            type="button"
                            onClick={() => {
                                setIsConfirmationOpen((current) => !current);
                            }}
                            disabled={!selectedCampaignId || isPreviewLoading}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isConfirmationOpen ? "Hide send confirmation" : "Review send confirmation"}
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                void handleExportAudiencePreview();
                            }}
                            disabled={!selectedCampaignId || isExportingPreview}
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isExportingPreview ? "Exporting..." : "Export audience CSV"}
                        </button>
                    </div>
                </div>

                {previewFeedbackMessage ? (
                    <div className={`mt-4 rounded-lg border px-4 py-3 text-sm ${previewFeedbackClasses}`}>
                        {previewFeedbackMessage}
                    </div>
                ) : null}

                {!selectedCampaignId ? (
                    <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                        Save a campaign draft to load its live preview, send confirmation, and execution snapshot history.
                    </div>
                ) : isPreviewLoading ? (
                    <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        Loading audience preview from the backend.
                    </div>
                ) : previewErrorMessage ? (
                    <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {previewErrorMessage}
                    </div>
                ) : !audiencePreview ? (
                    <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                        No audience preview is available yet for this campaign.
                    </div>
                ) : (
                    <div className="mt-6 space-y-6">
                        <div className="grid gap-4 md:grid-cols-3">
                            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    Live matched records
                                </p>
                                <p className="mt-2 text-2xl font-semibold text-slate-900">
                                    {audiencePreview.total_matched_records}
                                </p>
                                <p className="mt-1 text-sm text-slate-600">
                                    {audiencePreview.audience_summary.summary_label}
                                </p>
                            </div>
                            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                                    Live eligible recipients
                                </p>
                                <p className="mt-2 text-2xl font-semibold text-emerald-900">
                                    {audiencePreview.eligible_recipients}
                                </p>
                                <p className="mt-1 text-sm text-emerald-800">
                                    Ready for the selected {audiencePreview.campaign.channel} channel.
                                </p>
                            </div>
                            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                                    Live excluded recipients
                                </p>
                                <p className="mt-2 text-2xl font-semibold text-amber-900">
                                    {audiencePreview.excluded_recipients}
                                </p>
                                <p className="mt-1 text-sm text-amber-800">
                                    Derived from current tenant contact data only.
                                </p>
                            </div>
                        </div>

                        <div>
                            <h3 className="text-sm font-semibold text-slate-900">Live exclusion reasons</h3>
                            {renderExclusionChips(audiencePreview.exclusion_counts)}
                        </div>

                        {isConfirmationOpen ? (
                            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                                <div className="flex flex-wrap items-start justify-between gap-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-slate-900">Send confirmation</h3>
                                        <p className="mt-1 text-sm text-slate-600">
                                            Review the live counts that will be frozen into the execution snapshot when send starts.
                                        </p>
                                    </div>
                                    <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
                                        {selectedCampaign?.channel === "email" ? "Email execution" : "Not sendable here"}
                                    </span>
                                </div>

                                <div className="mt-4 grid gap-4 md:grid-cols-2">
                                    <div className="rounded-lg border border-slate-200 bg-white p-4">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                            Campaign
                                        </p>
                                        <p className="mt-2 text-sm font-semibold text-slate-900">
                                            {audiencePreview.campaign.name}
                                        </p>
                                        <p className="mt-1 text-sm text-slate-600">
                                            {formatLabel(audiencePreview.campaign.channel)} /{" "}
                                            {formatAudienceType(audiencePreview.campaign.audience_type)}
                                        </p>
                                    </div>
                                    <div className="rounded-lg border border-slate-200 bg-white p-4">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                            Frozen at send start
                                        </p>
                                        <div className="mt-2 space-y-1 text-sm text-slate-700">
                                            <p>Matched: {audiencePreview.total_matched_records}</p>
                                            <p>Eligible: {audiencePreview.eligible_recipients}</p>
                                            <p>Excluded: {audiencePreview.excluded_recipients}</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4">
                                    <h4 className="text-sm font-semibold text-slate-900">Exclusion reasons</h4>
                                    {renderExclusionChips(audiencePreview.exclusion_counts)}
                                </div>

                                {selectedCampaign?.channel !== "email" ? (
                                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                        Only email campaigns have an execution foundation in this slice.
                                    </div>
                                ) : null}

                                {sendBlockers.length > 0 ? (
                                    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        <p className="font-medium">Send is blocked by current grounded rules.</p>
                                        <ul className="mt-2 list-disc pl-5">
                                            {sendBlockers.map((reason) => (
                                                <li key={reason}>{reason}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ) : null}

                                <div className="mt-5 flex flex-wrap gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setIsConfirmationOpen(false)}
                                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            void handleConfirmSend();
                                        }}
                                        disabled={!canStartSend || isStartingSend}
                                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {isStartingSend ? "Starting send..." : "Confirm and start send"}
                                    </button>
                                </div>
                            </div>
                        ) : null}

                        {audiencePreview.send_readiness.blocked_reasons.length > 0 ? (
                            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                <p className="font-medium">Campaign rules currently block sending.</p>
                                <ul className="mt-2 list-disc pl-5">
                                    {audiencePreview.send_readiness.blocked_reasons.map((reason) => (
                                        <li key={reason}>{reason}</li>
                                    ))}
                                </ul>
                            </div>
                        ) : null}

                        {audiencePreview.total_matched_records === 0 ? (
                            <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                No contacts match this campaign audience yet. Adjust the audience scope or prepare more contacts first.
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-900">
                                            Live recipient sample
                                        </h3>
                                        <p className="mt-1 text-sm text-slate-600">
                                            Showing {audiencePreview.recipients.length} of{" "}
                                            {audiencePreview.total_matched_records} matched recipients.
                                        </p>
                                    </div>
                                    {audiencePreview.has_more_recipients ? (
                                        <p className="text-sm text-slate-600">
                                            This preview is sampled. Export the CSV for the full audience.
                                        </p>
                                    ) : null}
                                </div>

                                <div className="overflow-x-auto rounded-lg border border-slate-200">
                                    <table className="min-w-full divide-y divide-slate-200">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Contact
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Email
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Phone
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Company
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Status
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                    Reason
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-200 bg-white">
                                            {audiencePreview.recipients.map((recipient) => (
                                                <tr key={recipient.contact_id}>
                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                        {recipient.contact_name}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                        {recipient.email ?? "-"}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                        {recipient.phone ?? "-"}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                        {recipient.company ?? "-"}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm">
                                                        <span
                                                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${getEligibilityBadgeClasses(
                                                                recipient.eligibility_status,
                                                            )}`}
                                                        >
                                                            {formatLabel(recipient.eligibility_status)}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                        {recipient.exclusion_reason ||
                                                            "Eligible for the selected channel."}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div>
                    <h2 className="text-xl font-semibold text-slate-900">Execution history and review</h2>
                    <p className="mt-1 text-sm text-slate-600">
                        Review grounded campaign executions, inspect frozen recipient results, and export follow-up CSVs from persisted execution records only.
                    </p>
                </div>

                {!selectedCampaignId ? (
                    <div className="mt-6 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                        Select a campaign to inspect its execution history and recipient results.
                    </div>
                ) : isDetailLoading && !campaignDetail ? (
                    <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        Loading execution status from the backend.
                    </div>
                ) : detailErrorMessage && !campaignDetail ? (
                    <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {detailErrorMessage}
                    </div>
                ) : (
                    <div className="mt-6 space-y-6">
                        {isDetailLoading ? (
                            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                                Refreshing execution status from the backend.
                            </div>
                        ) : null}

                        {detailErrorMessage ? (
                            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                {detailErrorMessage}
                            </div>
                        ) : null}

                        {campaignDetail?.latest_execution ? (
                            <>
                                <div className="grid gap-4 lg:grid-cols-2">
                                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                            Live preview now
                                        </p>
                                        <div className="mt-2 space-y-1 text-sm text-slate-700">
                                            <p>Matched: {audiencePreview?.total_matched_records ?? "Unavailable"}</p>
                                            <p>Eligible: {audiencePreview?.eligible_recipients ?? "Unavailable"}</p>
                                            <p>Excluded: {audiencePreview?.excluded_recipients ?? "Unavailable"}</p>
                                        </div>
                                    </div>
                                    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                                            Frozen send snapshot
                                        </p>
                                        {campaignDetail.latest_execution_snapshot ? (
                                            <div className="mt-2 space-y-1 text-sm text-indigo-900">
                                                <p>Matched: {campaignDetail.latest_execution_snapshot.total_matched_records}</p>
                                                <p>Eligible: {campaignDetail.latest_execution_snapshot.eligible_recipients}</p>
                                                <p>Excluded: {campaignDetail.latest_execution_snapshot.excluded_recipients}</p>
                                            </div>
                                        ) : (
                                            <p className="mt-2 text-sm text-indigo-900">
                                                No frozen snapshot metadata was stored for this execution.
                                            </p>
                                        )}
                                    </div>
                                </div>

                                {campaignDetail.latest_execution_snapshot ? (
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-900">Snapshot exclusion reasons</h3>
                                        {renderExclusionChips(campaignDetail.latest_execution_snapshot.exclusion_counts)}
                                    </div>
                                ) : null}

                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                                    <div className="flex flex-wrap items-start justify-between gap-4">
                                        <div>
                                            <h3 className="text-lg font-semibold text-slate-900">Execution status</h3>
                                            <p className="mt-1 text-sm text-slate-600">
                                                This section reflects the real execution record only. No provider delivery telemetry is implied.
                                            </p>
                                            {hasActiveExecution ? (
                                                <p className="mt-2 text-sm text-slate-600">
                                                    Active execution refreshes automatically every {ACTIVE_EXECUTION_POLL_INTERVAL_MS / 1000} seconds.
                                                </p>
                                            ) : null}
                                        </div>
                                        <span
                                            className={`rounded-full px-3 py-1 text-xs font-medium ${getExecutionStatusBadgeClasses(
                                                campaignDetail.latest_execution.status,
                                            )}`}
                                        >
                                            {formatLabel(campaignDetail.latest_execution.status)}
                                        </span>
                                    </div>

                                    <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Requested
                                            </p>
                                            <p className="mt-2">{formatDateTime(campaignDetail.latest_execution.requested_at)}</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Started
                                            </p>
                                            <p className="mt-2">{formatDateTime(campaignDetail.latest_execution.started_at)}</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Completed
                                            </p>
                                            <p className="mt-2">{formatDateTime(campaignDetail.latest_execution.completed_at)}</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Queue job
                                            </p>
                                            <p className="mt-2">{campaignDetail.latest_execution.queue_job_id ?? "Not assigned"}</p>
                                        </div>
                                    </div>

                                    <div className="mt-4 grid gap-4 md:grid-cols-4">
                                        <div className="rounded-lg border border-slate-200 bg-white p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Snapshot recipients
                                            </p>
                                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                                {campaignDetail.latest_execution.total_recipients}
                                            </p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 bg-white p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                Processed
                                            </p>
                                            <p className="mt-2 text-2xl font-semibold text-slate-900">
                                                {campaignDetail.latest_execution.processed_recipients}
                                            </p>
                                        </div>
                                        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                                                Sent
                                            </p>
                                            <p className="mt-2 text-2xl font-semibold text-emerald-900">
                                                {campaignDetail.latest_execution.sent_recipients}
                                            </p>
                                        </div>
                                        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-red-700">
                                                Failed
                                            </p>
                                            <p className="mt-2 text-2xl font-semibold text-red-900">
                                                {campaignDetail.latest_execution.failed_recipients}
                                            </p>
                                        </div>
                                    </div>

                                    {campaignDetail.latest_execution.blocked_reason ? (
                                        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                            {campaignDetail.latest_execution.blocked_reason}
                                        </div>
                                    ) : null}
                                </div>

                                {campaignDetail.recent_recipients.length === 0 ? (
                                    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                        No execution recipients have been captured for this snapshot yet.
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-900">
                                                Frozen recipient sample
                                            </h3>
                                            <p className="mt-1 text-sm text-slate-600">
                                                Showing recipients from the latest execution snapshot, not the live preview.
                                            </p>
                                        </div>

                                        <div className="overflow-x-auto rounded-lg border border-slate-200">
                                            <table className="min-w-full divide-y divide-slate-200">
                                                <thead className="bg-slate-50">
                                                    <tr>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Contact
                                                        </th>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Email
                                                        </th>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Phone
                                                        </th>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Company
                                                        </th>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Execution status
                                                        </th>
                                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                            Failure reason
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-200 bg-white">
                                                    {campaignDetail.recent_recipients.map((recipient) => (
                                                        <tr key={recipient.id}>
                                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                                {buildExecutionRecipientLabel(recipient)}
                                                            </td>
                                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                                {recipient.email}
                                                            </td>
                                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                                {recipient.phone ?? "-"}
                                                            </td>
                                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                                {recipient.company ?? "-"}
                                                            </td>
                                                            <td className="px-4 py-3 text-sm">
                                                                <span
                                                                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${getExecutionStatusBadgeClasses(
                                                                        recipient.status,
                                                                    )}`}
                                                                >
                                                                    {formatLabel(recipient.status)}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                                {recipient.failure_reason ?? "-"}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                No execution has started for this campaign yet.
                            </div>
                        )}

                        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.4fr]">
                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900">Execution history</h3>
                                    <p className="mt-1 text-sm text-slate-600">
                                        Recent executions are listed in descending requested order from the grounded execution table.
                                    </p>
                                </div>

                                {!campaignDetail || campaignDetail.execution_history.length === 0 ? (
                                    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                        No prior executions have been recorded for this campaign yet.
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {campaignDetail.execution_history.map((execution) => (
                                            <button
                                                key={execution.id}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedExecutionId(execution.id);
                                                    setSelectedRecipientFilter(
                                                        getDefaultExecutionRecipientFilter(execution),
                                                    );
                                                    setExecutionFeedbackMessage("");
                                                }}
                                                className={`w-full rounded-xl border px-4 py-4 text-left transition ${
                                                    execution.id === selectedExecutionId
                                                        ? "border-slate-900 bg-slate-50"
                                                        : "border-slate-200 hover:border-slate-300"
                                                }`}
                                            >
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-semibold text-slate-900">
                                                            Execution {formatExecutionLabel(execution.id)}
                                                        </p>
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            Requested {formatDateTime(execution.requested_at)}
                                                        </p>
                                                    </div>
                                                    <span
                                                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${getExecutionStatusBadgeClasses(
                                                            execution.status,
                                                        )}`}
                                                    >
                                                        {formatLabel(execution.status)}
                                                    </span>
                                                </div>
                                                <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                                                    <p>Recipients: {execution.total_recipients}</p>
                                                    <p>Processed: {execution.processed_recipients}</p>
                                                    <p>Sent: {execution.sent_recipients}</p>
                                                    <p>Failed: {execution.failed_recipients}</p>
                                                </div>
                                                <p className="mt-2 text-xs text-slate-500">
                                                    Queue job: {execution.queue_job_id ?? "Not assigned"}
                                                </p>
                                                {execution.blocked_reason ? (
                                                    <p className="mt-2 text-xs text-amber-700">
                                                        {execution.blocked_reason}
                                                    </p>
                                                ) : null}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="space-y-4">
                                <div className="flex flex-wrap items-start justify-between gap-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-slate-900">
                                            Failed recipient follow-up
                                        </h3>
                                        <p className="mt-1 text-sm text-slate-600">
                                            This review stays grounded in persisted execution recipient rows. Failed recipients are shown first when the selected execution contains failures.
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap gap-3">
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setIsFollowUpConfirmationOpen((current) => !current);
                                            }}
                                            disabled={selectedVisibleFailedRecipients.length === 0}
                                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {isFollowUpConfirmationOpen ? "Hide handoff confirmation" : "Create follow-up tasks"}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                void handleExportExecutionResults();
                                            }}
                                            disabled={!selectedExecutionId || isExportingExecutionResults}
                                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {isExportingExecutionResults ? "Exporting..." : "Export execution CSV"}
                                        </button>
                                    </div>
                                </div>

                                {executionFeedbackMessage ? (
                                    <div className={`rounded-lg border px-4 py-3 text-sm ${executionFeedbackClasses}`}>
                                        {executionFeedbackMessage}
                                    </div>
                                ) : null}

                                {!selectedExecutionId ? (
                                    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                        Select an execution from history to inspect recipient results.
                                    </div>
                                ) : isExecutionDetailLoading && !executionDetail ? (
                                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                                        Loading selected execution results from the backend.
                                    </div>
                                ) : executionDetailErrorMessage && !executionDetail ? (
                                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                        {executionDetailErrorMessage}
                                    </div>
                                ) : !executionDetail ? (
                                    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                        No execution detail is available for the current selection.
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {executionDetailErrorMessage ? (
                                            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                                {executionDetailErrorMessage}
                                            </div>
                                        ) : null}

                                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                                            <div className="flex flex-wrap items-start justify-between gap-4">
                                                <div>
                                                    <p className="text-sm font-semibold text-slate-900">
                                                        Execution {formatExecutionLabel(executionDetail.execution.id)}
                                                    </p>
                                                    <p className="mt-1 text-sm text-slate-600">
                                                        Requested {formatDateTime(executionDetail.execution.requested_at)}
                                                    </p>
                                                </div>
                                                <span
                                                    className={`rounded-full px-3 py-1 text-xs font-medium ${getExecutionStatusBadgeClasses(
                                                        executionDetail.execution.status,
                                                    )}`}
                                                >
                                                    {formatLabel(executionDetail.execution.status)}
                                                </span>
                                            </div>

                                            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                                <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                        Started
                                                    </p>
                                                    <p className="mt-2">{formatDateTime(executionDetail.execution.started_at)}</p>
                                                </div>
                                                <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                        Completed
                                                    </p>
                                                    <p className="mt-2">{formatDateTime(executionDetail.execution.completed_at)}</p>
                                                </div>
                                                <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                        Queue job
                                                    </p>
                                                    <p className="mt-2">{executionDetail.execution.queue_job_id ?? "Not assigned"}</p>
                                                </div>
                                                <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                        Recipients
                                                    </p>
                                                    <p className="mt-2">{executionDetail.execution.total_recipients}</p>
                                                </div>
                                            </div>

                                            {executionDetail.execution_snapshot ? (
                                                <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-900">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                                                        Selected execution snapshot
                                                    </p>
                                                    <div className="mt-2 grid gap-2 md:grid-cols-3">
                                                        <p>Matched: {executionDetail.execution_snapshot.total_matched_records}</p>
                                                        <p>Eligible: {executionDetail.execution_snapshot.eligible_recipients}</p>
                                                        <p>Excluded: {executionDetail.execution_snapshot.excluded_recipients}</p>
                                                    </div>
                                                </div>
                                            ) : null}

                                            {executionDetail.execution.blocked_reason ? (
                                                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                                                    {executionDetail.execution.blocked_reason}
                                                </div>
                                            ) : null}
                                        </div>

                                        <div className="space-y-3">
                                            <div className="flex flex-wrap gap-2">
                                                {(
                                                    ["failed", "all", "sent", "pending", "blocked"] as MarketingExecutionRecipientResultFilter[]
                                                ).map((filterValue) => (
                                                    <button
                                                        key={filterValue}
                                                        type="button"
                                                        onClick={() => setSelectedRecipientFilter(filterValue)}
                                                        className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                                                            selectedRecipientFilter === filterValue
                                                                ? "bg-slate-900 text-white"
                                                                : "border border-slate-300 text-slate-700 hover:bg-slate-100"
                                                        }`}
                                                    >
                                                        {formatLabel(filterValue)} (
                                                        {getExecutionRecipientFilterCount(
                                                            executionDetail,
                                                            filterValue,
                                                        )}
                                                        )
                                                    </button>
                                                ))}
                                            </div>

                                            {visibleFailedRecipients.length === 0 ? (
                                                <div className="rounded-lg border border-dashed border-slate-300 px-4 py-4 text-sm text-slate-600">
                                                    No failed recipients are available in the current filtered view for follow-up handoff.
                                                </div>
                                            ) : (
                                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                                        <div>
                                                            <p className="text-sm font-semibold text-slate-900">
                                                                Failed recipient selection
                                                            </p>
                                                            <p className="mt-1 text-sm text-slate-600">
                                                                Select individual failed recipients or all failed recipients visible in the current filter before creating support-ticket follow-up tasks.
                                                            </p>
                                                        </div>
                                                        <button
                                                            type="button"
                                                            onClick={toggleSelectAllVisibleFailedRecipients}
                                                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                                                        >
                                                            {allVisibleFailedRecipientsSelected
                                                                ? "Clear selected failed recipients"
                                                                : "Select all failed recipients in view"}
                                                        </button>
                                                    </div>
                                                    <p className="mt-3 text-sm text-slate-700">
                                                        {selectedVisibleFailedRecipients.length} failed recipient
                                                        {selectedVisibleFailedRecipients.length === 1 ? "" : "s"} selected
                                                    </p>
                                                </div>
                                            )}

                                            {isFollowUpConfirmationOpen ? (
                                                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                                                    <p className="text-sm font-semibold text-amber-900">
                                                        Confirm follow-up handoff
                                                    </p>
                                                    <p className="mt-2 text-sm text-amber-900">
                                                        This will create {selectedVisibleFailedRecipients.length} support ticket
                                                        {selectedVisibleFailedRecipients.length === 1 ? "" : "s"} for the selected failed recipients using the current persisted execution results.
                                                    </p>
                                                    <div className="mt-4 flex flex-wrap gap-3">
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                void handleConfirmFollowUpHandoff();
                                                            }}
                                                            disabled={isSubmittingFollowUpHandoff}
                                                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            {isSubmittingFollowUpHandoff ? "Creating..." : "Confirm follow-up handoff"}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => setIsFollowUpConfirmationOpen(false)}
                                                            disabled={isSubmittingFollowUpHandoff}
                                                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            Cancel
                                                        </button>
                                                    </div>
                                                </div>
                                            ) : null}

                                            {executionDetail.recipients.length === 0 ? (
                                                <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                                                    No {selectedRecipientFilter === "all" ? "" : `${selectedRecipientFilter} `}
                                                    recipients were recorded for this execution selection.
                                                </div>
                                            ) : (
                                                <div className="overflow-x-auto rounded-lg border border-slate-200">
                                                    <table className="min-w-full divide-y divide-slate-200">
                                                        <thead className="bg-slate-50">
                                                            <tr>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Select
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Contact
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Email
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Phone
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Company
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Status
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Failure reason
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Support ticket
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Handoff
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Sent at
                                                                </th>
                                                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                    Batch
                                                                </th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-slate-200 bg-white">
                                                            {executionDetail.recipients.map((recipient) => (
                                                                <tr key={recipient.id}>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.status === "failed" ? (
                                                                            <input
                                                                                type="checkbox"
                                                                                aria-label={`Select failed recipient ${recipient.contact_name}`}
                                                                                checked={selectedFailedRecipientIds.includes(recipient.id)}
                                                                                onChange={() => toggleFailedRecipientSelection(recipient.id)}
                                                                                className="h-4 w-4 rounded border-slate-300"
                                                                            />
                                                                        ) : (
                                                                            <span className="text-xs text-slate-400">Only failed</span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {buildExecutionRecipientLabel(recipient)}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.email}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.phone ?? "-"}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.company ?? "-"}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        <span
                                                                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${getExecutionStatusBadgeClasses(
                                                                                recipient.status,
                                                                            )}`}
                                                                        >
                                                                            {formatLabel(recipient.status)}
                                                                        </span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.failure_reason ?? "-"}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.support_ticket_id ? (
                                                                            <Link
                                                                                href={`/support/${recipient.support_ticket_id}`}
                                                                                className="text-slate-900 underline underline-offset-2"
                                                                            >
                                                                                {recipient.support_ticket_id}
                                                                            </Link>
                                                                        ) : (
                                                                            "-"
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        <div className="space-y-1">
                                                                            <p>{formatHandoffStatus(recipient.handoff_status)}</p>
                                                                            {recipient.handoff_at ? (
                                                                                <p className="text-xs text-slate-500">
                                                                                    {formatDateTime(recipient.handoff_at)}
                                                                                </p>
                                                                            ) : null}
                                                                            {recipient.handoff_by_user_id ? (
                                                                                <p className="text-xs text-slate-500">
                                                                                    By {recipient.handoff_by_user_id}
                                                                                </p>
                                                                            ) : null}
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {formatDateTime(recipient.sent_at)}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-slate-700">
                                                                        {recipient.batch_number}
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
}
