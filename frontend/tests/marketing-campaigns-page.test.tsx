import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getMarketingCampaigns: vi.fn(),
    getMarketingCampaignDetail: vi.fn(),
    getMarketingCampaignExecutionDetail: vi.fn(),
    getMarketingCampaignAudiencePreview: vi.fn(),
    createMarketingExecutionFollowUpHandoff: vi.fn(),
    exportMarketingCampaignAudiencePreviewCsv: vi.fn(),
    exportMarketingCampaignExecutionResultsCsv: vi.fn(),
    startMarketingCampaignEmailSend: vi.fn(),
    createMarketingCampaign: vi.fn(),
    updateMarketingCampaign: vi.fn(),
    triggerBrowserDownload: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

vi.mock("@/services/marketing.service", () => ({
    getMarketingCampaigns: mocks.getMarketingCampaigns,
    getMarketingCampaignDetail: mocks.getMarketingCampaignDetail,
    getMarketingCampaignExecutionDetail: mocks.getMarketingCampaignExecutionDetail,
    getMarketingCampaignAudiencePreview: mocks.getMarketingCampaignAudiencePreview,
    createMarketingExecutionFollowUpHandoff: mocks.createMarketingExecutionFollowUpHandoff,
    exportMarketingCampaignAudiencePreviewCsv: mocks.exportMarketingCampaignAudiencePreviewCsv,
    exportMarketingCampaignExecutionResultsCsv: mocks.exportMarketingCampaignExecutionResultsCsv,
    startMarketingCampaignEmailSend: mocks.startMarketingCampaignEmailSend,
    createMarketingCampaign: mocks.createMarketingCampaign,
    updateMarketingCampaign: mocks.updateMarketingCampaign,
}));

vi.mock("@/lib/download-file", () => ({
    triggerBrowserDownload: mocks.triggerBrowserDownload,
}));

import MarketingCampaignsManager from "@/components/marketing/MarketingCampaignsManager";

const baseCampaign = {
    id: "campaign-1",
    tenant_id: "tenant-1",
    name: "Spring launch",
    channel: "email" as const,
    audience_type: "all_contacts" as const,
    audience_description: "Qualified contacts",
    target_company_id: null,
    target_contact_id: null,
    subject: "Launch update",
    message_body: "Hello from SupaCRM",
    status: "draft" as const,
    scheduled_for: null,
    created_at: "2026-04-12T10:00:00Z",
    updated_at: "2026-04-12T10:00:00Z",
};

const basePreview = {
    campaign: baseCampaign,
    audience_summary: {
        audience_type: "all_contacts" as const,
        summary_label: "All contacts in the current tenant",
        target_company_label: null,
        target_contact_label: null,
        total_contacts: 3,
        email_eligible_contacts: 1,
        blocked_reasons: [],
    },
    send_readiness: {
        channel: "email" as const,
        can_send: true,
        smtp_ready: true,
        queue_ready: true,
        blocked_reasons: [],
        capacity_note: "Launch scope only.",
    },
    total_matched_records: 3,
    eligible_recipients: 1,
    excluded_recipients: 2,
    exclusion_counts: [
        { reason: "missing_email" as const, count: 1 },
        { reason: "duplicate_contact_method" as const, count: 1 },
    ],
    sample_limit: 25,
    has_more_recipients: false,
    recipients: [
        {
            contact_id: "contact-1",
            contact_name: "Alicia Andersson",
            email: "alicia@example.com",
            phone: "+46700000000",
            company: "Northwind",
            eligibility_status: "eligible" as const,
            exclusion_reason: null,
        },
        {
            contact_id: "contact-2",
            contact_name: "Bjorn Berg",
            email: "alicia@example.com",
            phone: "+46700000001",
            company: "Northwind",
            eligibility_status: "duplicate_contact_method" as const,
            exclusion_reason: "Duplicate contact method in this campaign preview.",
        },
    ],
};

const emptyRecipientTraceability = {
    support_ticket_id: null,
    handoff_at: null,
    handoff_by_user_id: null,
    handoff_status: null,
};

const baseDetail = {
    campaign: {
        ...baseCampaign,
        status: "sending" as const,
    },
    audience_summary: basePreview.audience_summary,
    send_readiness: basePreview.send_readiness,
    latest_execution: {
        id: "execution-1",
        tenant_id: "tenant-1",
        campaign_id: "campaign-1",
        channel: "email" as const,
        status: "sending" as const,
        total_recipients: 1,
        processed_recipients: 0,
        sent_recipients: 0,
        failed_recipients: 0,
        batch_size: 100,
        queued_batch_count: 1,
        queue_job_id: "job-1",
        blocked_reason: null,
        requested_at: "2026-04-21T10:00:00Z",
        started_at: "2026-04-21T10:00:02Z",
        completed_at: null,
        created_at: "2026-04-21T10:00:00Z",
        updated_at: "2026-04-21T10:00:02Z",
    },
    latest_execution_snapshot: {
        audience_type: "all_contacts" as const,
        summary_label: "All contacts in the current tenant",
        target_company_label: null,
        target_contact_label: null,
        total_matched_records: 2,
        eligible_recipients: 1,
        excluded_recipients: 1,
        exclusion_counts: [{ reason: "missing_email" as const, count: 1 }],
    },
    recent_recipients: [
        {
            ...emptyRecipientTraceability,
            id: "recipient-1",
            execution_id: "execution-1",
            campaign_id: "campaign-1",
            contact_id: "contact-1",
            contact_name: "Alicia Andersson",
            email: "alicia@example.com",
            phone: "+46700000000",
            first_name: "Alicia",
            last_name: "Andersson",
            company: "Northwind",
            batch_number: 1,
            status: "pending" as const,
            failure_reason: null,
            sent_at: null,
        },
    ],
    execution_history: [
        {
            id: "execution-1",
            tenant_id: "tenant-1",
            campaign_id: "campaign-1",
            channel: "email" as const,
            status: "sending" as const,
            total_recipients: 1,
            processed_recipients: 0,
            sent_recipients: 0,
            failed_recipients: 0,
            batch_size: 100,
            queued_batch_count: 1,
            queue_job_id: "job-1",
            blocked_reason: null,
            requested_at: "2026-04-21T10:00:00Z",
            started_at: "2026-04-21T10:00:02Z",
            completed_at: null,
            created_at: "2026-04-21T10:00:00Z",
            updated_at: "2026-04-21T10:00:02Z",
        },
        {
            id: "execution-0",
            tenant_id: "tenant-1",
            campaign_id: "campaign-1",
            channel: "email" as const,
            status: "failed" as const,
            total_recipients: 2,
            processed_recipients: 2,
            sent_recipients: 1,
            failed_recipients: 1,
            batch_size: 100,
            queued_batch_count: 1,
            queue_job_id: "job-0",
            blocked_reason: "One recipient failed.",
            requested_at: "2026-04-20T10:00:00Z",
            started_at: "2026-04-20T10:00:02Z",
            completed_at: "2026-04-20T10:01:00Z",
            created_at: "2026-04-20T10:00:00Z",
            updated_at: "2026-04-20T10:01:00Z",
        },
    ],
};

const queuedDetail = {
    ...baseDetail,
    latest_execution: {
        ...baseDetail.latest_execution,
        status: "queued" as const,
        started_at: null,
        processed_recipients: 0,
        sent_recipients: 0,
        failed_recipients: 0,
    },
    recent_recipients: [
        {
            ...baseDetail.recent_recipients[0],
            status: "pending" as const,
            failure_reason: null,
            sent_at: null,
        },
    ],
};

const completedDetail = {
    ...baseDetail,
    latest_execution: {
        ...baseDetail.latest_execution,
        status: "completed" as const,
        processed_recipients: 1,
        sent_recipients: 1,
        failed_recipients: 0,
        completed_at: "2026-04-21T10:01:00Z",
    },
    recent_recipients: [
        {
            ...baseDetail.recent_recipients[0],
            status: "sent" as const,
            sent_at: "2026-04-21T10:00:30Z",
        },
    ],
};

const latestExecutionReview = {
    execution: baseDetail.latest_execution,
    execution_snapshot: baseDetail.latest_execution_snapshot,
    recipient_filter: "all" as const,
    recipient_counts: [
        { status: "all" as const, count: 1 },
        { status: "failed" as const, count: 0 },
        { status: "sent" as const, count: 0 },
        { status: "pending" as const, count: 1 },
        { status: "blocked" as const, count: 0 },
    ],
    recipients: baseDetail.recent_recipients,
};

const failedExecutionReview = {
    execution: baseDetail.execution_history[1],
    execution_snapshot: {
        audience_type: "all_contacts" as const,
        summary_label: "All contacts in the current tenant",
        target_company_label: null,
        target_contact_label: null,
        total_matched_records: 2,
        eligible_recipients: 2,
        excluded_recipients: 0,
        exclusion_counts: [],
    },
    recipient_filter: "failed" as const,
    recipient_counts: [
        { status: "all" as const, count: 2 },
        { status: "failed" as const, count: 1 },
        { status: "sent" as const, count: 1 },
        { status: "pending" as const, count: 0 },
        { status: "blocked" as const, count: 0 },
    ],
    recipients: [
        {
            support_ticket_id: "ticket-1",
            handoff_at: "2026-04-20T10:02:00Z",
            handoff_by_user_id: "user-alpha",
            handoff_status: "created" as const,
            id: "recipient-2",
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            contact_id: "contact-2",
            contact_name: "Bjorn Berg",
            email: "bjorn@example.com",
            phone: "+46700000001",
            first_name: "Bjorn",
            last_name: "Berg",
            company: "Northwind",
            batch_number: 1,
            status: "failed" as const,
            failure_reason: "SMTP recipient rejected",
            sent_at: null,
        },
    ],
};

const failedExecutionReviewAll = {
    ...failedExecutionReview,
    recipient_filter: "all" as const,
    recipients: [
        {
            support_ticket_id: "ticket-1",
            handoff_at: "2026-04-20T10:02:00Z",
            handoff_by_user_id: "user-alpha",
            handoff_status: "created" as const,
            id: "recipient-2",
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            contact_id: "contact-2",
            contact_name: "Bjorn Berg",
            email: "bjorn@example.com",
            phone: "+46700000001",
            first_name: "Bjorn",
            last_name: "Berg",
            company: "Northwind",
            batch_number: 1,
            status: "failed" as const,
            failure_reason: "SMTP recipient rejected",
            sent_at: null,
        },
        {
            ...emptyRecipientTraceability,
            id: "recipient-3",
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            contact_id: "contact-1",
            contact_name: "Alicia Andersson",
            email: "alicia@example.com",
            phone: "+46700000000",
            first_name: "Alicia",
            last_name: "Andersson",
            company: "Northwind",
            batch_number: 1,
            status: "sent" as const,
            failure_reason: null,
            sent_at: "2026-04-20T10:00:40Z",
        },
    ],
};

beforeEach(() => {
    mocks.getCompanies.mockReset();
    mocks.getContacts.mockReset();
    mocks.getMarketingCampaigns.mockReset();
    mocks.getMarketingCampaignDetail.mockReset();
    mocks.getMarketingCampaignExecutionDetail.mockReset();
    mocks.getMarketingCampaignAudiencePreview.mockReset();
    mocks.createMarketingExecutionFollowUpHandoff.mockReset();
    mocks.exportMarketingCampaignAudiencePreviewCsv.mockReset();
    mocks.exportMarketingCampaignExecutionResultsCsv.mockReset();
    mocks.startMarketingCampaignEmailSend.mockReset();
    mocks.createMarketingCampaign.mockReset();
    mocks.updateMarketingCampaign.mockReset();
    mocks.triggerBrowserDownload.mockReset();

    mocks.getCompanies.mockResolvedValue({
        items: [{ id: "company-1", name: "Northwind", tenant_id: "tenant-1" }],
        total: 1,
    });
    mocks.getContacts.mockResolvedValue({
        items: [
            {
                id: "contact-1",
                tenant_id: "tenant-1",
                first_name: "Alicia",
                last_name: "Andersson",
                email: "alicia@example.com",
                phone: "+46700000000",
                company_id: "company-1",
                company: "Northwind",
                job_title: null,
                notes: null,
                created_at: "2026-04-12T10:00:00Z",
                updated_at: "2026-04-12T10:00:00Z",
            },
        ],
        total: 1,
    });
    mocks.getMarketingCampaigns.mockResolvedValue({
        items: [baseCampaign],
        total: 1,
    });
    mocks.getMarketingCampaignDetail.mockResolvedValue(baseDetail);
    mocks.getMarketingCampaignExecutionDetail.mockImplementation(
        async (_campaignId: string, executionId: string, params?: { recipient_status?: string }) => {
            if (executionId === "execution-0") {
                return params?.recipient_status === "all"
                    ? failedExecutionReviewAll
                    : failedExecutionReview;
            }
            return latestExecutionReview;
        },
    );
    mocks.getMarketingCampaignAudiencePreview.mockResolvedValue(basePreview);
    mocks.createMarketingExecutionFollowUpHandoff.mockResolvedValue({
        execution_id: "execution-0",
        campaign_id: "campaign-1",
        requested_count: 1,
        created_count: 1,
        failed_count: 0,
        results: [
            {
                recipient_id: "recipient-2",
                contact_name: "Bjorn Berg",
                email: "bjorn@example.com",
                status: "created",
                support_ticket_id: "ticket-1",
                message: null,
            },
        ],
    });
    mocks.exportMarketingCampaignAudiencePreviewCsv.mockResolvedValue({
        blob: new Blob(["csv"], { type: "text/csv" }),
        filename: "campaign-audience-preview.csv",
        rowCount: 3,
    });
    mocks.exportMarketingCampaignExecutionResultsCsv.mockResolvedValue({
        blob: new Blob(["csv"], { type: "text/csv" }),
        filename: "campaign-execution-results-execution-1.csv",
        rowCount: 1,
    });
    mocks.startMarketingCampaignEmailSend.mockResolvedValue(baseDetail);
    mocks.createMarketingCampaign.mockResolvedValue(baseCampaign);
    mocks.updateMarketingCampaign.mockResolvedValue(baseCampaign);
});

afterEach(() => {
    vi.useRealTimers();
    cleanup();
});

describe("marketing campaigns", () => {
    it("renders live preview and frozen latest execution snapshot side by side", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignDetail).toHaveBeenCalledWith("campaign-1");
            expect(mocks.getMarketingCampaignAudiencePreview).toHaveBeenCalledWith("campaign-1", {
                sample_limit: 25,
            });
        });

        await waitFor(() => {
            expect(screen.getByText("Live preview now")).toBeTruthy();
        });

        expect(screen.getByText("Live preview now")).toBeTruthy();
        expect(screen.getByText("Frozen send snapshot")).toBeTruthy();
        expect(screen.getByText("Matched: 3")).toBeTruthy();
        expect(screen.getByText("Matched: 2")).toBeTruthy();
        expect(screen.getByText("Queue job")).toBeTruthy();
        expect(screen.getByText("job-1")).toBeTruthy();
        expect(screen.getByText("Frozen recipient sample")).toBeTruthy();
        expect(screen.getAllByText("Alicia Andersson").length).toBeGreaterThan(0);
    });

    it("opens send confirmation and starts send with explicit operator action", async () => {
        mocks.startMarketingCampaignEmailSend.mockResolvedValue(queuedDetail);
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignAudiencePreview).toHaveBeenCalledTimes(1);
        });

        await waitFor(() => {
            expect(screen.getByText("Live matched records")).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Review send confirmation/i }));

        expect(screen.getByText("Send confirmation")).toBeTruthy();
        expect(screen.getByText("Frozen at send start")).toBeTruthy();
        expect(screen.getAllByText("Matched: 3").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Eligible: 1").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Excluded: 2").length).toBeGreaterThan(0);

        fireEvent.click(screen.getByRole("button", { name: /Confirm and start send/i }));

        await waitFor(() => {
            expect(mocks.startMarketingCampaignEmailSend).toHaveBeenCalledWith("campaign-1");
        });

        expect(
            screen.getByText("Campaign send queued with a frozen audience snapshot."),
        ).toBeTruthy();
    });

    it("polls the active execution area until the latest execution completes", async () => {
        mocks.getMarketingCampaignDetail.mockResolvedValueOnce(baseDetail).mockResolvedValueOnce(completedDetail);

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getAllByText("Execution status").length).toBeGreaterThan(0);
        });

        expect(
            screen.getByText("Active execution refreshes automatically every 3 seconds."),
        ).toBeTruthy();

        await waitFor(() => {
            expect(mocks.getMarketingCampaignDetail).toHaveBeenCalledTimes(2);
        }, { timeout: 4500 });

        expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Sent").length).toBeGreaterThan(0);
    }, 9000);

    it("exports the audience preview CSV from the campaign screen", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignAudiencePreview).toHaveBeenCalledTimes(1);
        });

        fireEvent.click(screen.getByRole("button", { name: /Export audience CSV/i }));

        await waitFor(() => {
            expect(mocks.exportMarketingCampaignAudiencePreviewCsv).toHaveBeenCalledWith("campaign-1");
        });

        expect(mocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
        expect(
            screen.getByText("Exported 3 recipients to campaign-audience-preview.csv."),
        ).toBeTruthy();
    });

    it("renders execution history and loads the selected execution review", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignExecutionDetail).toHaveBeenCalledWith(
                "campaign-1",
                "execution-1",
                { recipient_status: "all" },
            );
        });

        expect(screen.getByText("Execution history")).toBeTruthy();
        expect(screen.getByText("Execution execution-0")).toBeTruthy();
        expect(screen.getByText("Failed recipient follow-up")).toBeTruthy();
    });

    it("selects an older execution and defaults failed-recipient review when failures exist", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignExecutionDetail).toHaveBeenCalledWith(
                "campaign-1",
                "execution-0",
                { recipient_status: "failed" },
            );
        });

        expect(screen.getByText("SMTP recipient rejected")).toBeTruthy();
        expect(screen.getByText("Failed (1)")).toBeTruthy();
    });

    it("shows support ticket traceability for handed-off failed recipients", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));

        const ticketLink = await screen.findByRole("link", { name: "ticket-1" });

        expect(ticketLink.getAttribute("href")).toContain("/support/ticket-1");
        expect(screen.getByText("Created")).toBeTruthy();
        expect(screen.getByText("By user-alpha")).toBeTruthy();
    });

    it("updates failed-recipient filtering for the selected execution", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));

        await waitFor(() => {
            expect(screen.getByText("Failed (1)")).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: "All (2)" }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignExecutionDetail).toHaveBeenCalledWith(
                "campaign-1",
                "execution-0",
                { recipient_status: "all" },
            );
        });
    });

    it("exports the selected execution CSV from the campaign screen", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignExecutionDetail).toHaveBeenCalledWith(
                "campaign-1",
                "execution-1",
                { recipient_status: "all" },
            );
        });

        fireEvent.click(screen.getByRole("button", { name: /Export execution CSV/i }));

        await waitFor(() => {
            expect(mocks.exportMarketingCampaignExecutionResultsCsv).toHaveBeenCalledWith(
                "campaign-1",
                "execution-1",
                { recipient_status: "all" },
            );
        });

        expect(mocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
        expect(
            screen.getByText("Exported 1 execution result to campaign-execution-results-execution-1.csv."),
        ).toBeTruthy();
    });

    it("shows honest empty execution states when a campaign has no prior executions", async () => {
        mocks.getMarketingCampaignDetail.mockResolvedValue({
            ...baseDetail,
            latest_execution: null,
            latest_execution_snapshot: null,
            execution_history: [],
            recent_recipients: [],
        });

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("No execution has started for this campaign yet.")).toBeTruthy();
        });

        expect(screen.getByText("No prior executions have been recorded for this campaign yet.")).toBeTruthy();
    });

    it("keeps the campaign page usable when selected execution detail fails to load", async () => {
        mocks.getMarketingCampaignExecutionDetail.mockRejectedValueOnce(new Error("execution detail failed"));

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(mocks.getMarketingCampaignExecutionDetail).toHaveBeenCalled();
        });

        expect(
            await screen.findByText("execution detail failed"),
        ).toBeTruthy();
        expect(screen.getByText("Execution history")).toBeTruthy();
        expect(screen.getByText("Live preview now")).toBeTruthy();
    });

    it("selects failed recipients and confirms follow-up handoff", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));

        await waitFor(() => {
            expect(screen.getByLabelText("Select failed recipient Bjorn Berg")).toBeTruthy();
        });

        fireEvent.click(screen.getByLabelText("Select failed recipient Bjorn Berg"));
        fireEvent.click(screen.getByRole("button", { name: /Create follow-up tasks/i }));

        expect(screen.getByRole("button", { name: /Confirm follow-up handoff/i })).toBeTruthy();

        fireEvent.click(screen.getByRole("button", { name: /Confirm follow-up handoff/i }));

        await waitFor(() => {
            expect(mocks.createMarketingExecutionFollowUpHandoff).toHaveBeenCalledWith(
                "campaign-1",
                "execution-0",
                {
                    recipient_ids: ["recipient-2"],
                    priority: "high",
                },
            );
        });

        expect(screen.getByText("Created 1 follow-up task from failed recipients.")).toBeTruthy();
    });

    it("supports select-all failed recipients in the current filtered view", async () => {
        mocks.createMarketingExecutionFollowUpHandoff.mockResolvedValue({
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            requested_count: 1,
            created_count: 1,
            failed_count: 0,
            results: [
                {
                    recipient_id: "recipient-2",
                    contact_name: "Bjorn Berg",
                    email: "bjorn@example.com",
                    status: "created",
                    support_ticket_id: "ticket-1",
                    message: null,
                },
            ],
        });

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Select all failed recipients in view/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Select all failed recipients in view/i }));
        fireEvent.click(screen.getByRole("button", { name: /Create follow-up tasks/i }));
        fireEvent.click(screen.getByRole("button", { name: /Confirm follow-up handoff/i }));

        await waitFor(() => {
            expect(mocks.createMarketingExecutionFollowUpHandoff).toHaveBeenCalledWith(
                "campaign-1",
                "execution-0",
                {
                    recipient_ids: ["recipient-2"],
                    priority: "high",
                },
            );
        });
    });

    it("shows mixed handoff success and failure feedback without silent skips", async () => {
        mocks.getMarketingCampaignExecutionDetail.mockImplementation(
            async (_campaignId: string, executionId: string, params?: { recipient_status?: string }) => {
                if (executionId === "execution-0") {
                    return params?.recipient_status === "all"
                        ? {
                              ...failedExecutionReviewAll,
                              recipient_counts: [
                                  { status: "all" as const, count: 3 },
                                  { status: "failed" as const, count: 2 },
                                  { status: "sent" as const, count: 1 },
                                  { status: "pending" as const, count: 0 },
                                  { status: "blocked" as const, count: 0 },
                              ],
                              recipients: [
                                  ...failedExecutionReviewAll.recipients,
                                  {
                                      ...emptyRecipientTraceability,
                                      id: "recipient-4",
                                      execution_id: "execution-0",
                                      campaign_id: "campaign-1",
                                      contact_id: "contact-4",
                                      contact_name: "Dana Dahl",
                                      email: "dana@example.com",
                                      phone: "+46700000003",
                                      first_name: "Dana",
                                      last_name: "Dahl",
                                      company: "Northwind",
                                      batch_number: 1,
                                      status: "failed" as const,
                                      failure_reason: "Mailbox unavailable",
                                      sent_at: null,
                                  },
                              ],
                          }
                        : {
                              ...failedExecutionReview,
                              recipient_counts: [
                                  { status: "all" as const, count: 3 },
                                  { status: "failed" as const, count: 2 },
                                  { status: "sent" as const, count: 1 },
                                  { status: "pending" as const, count: 0 },
                                  { status: "blocked" as const, count: 0 },
                              ],
                              recipients: [
                                  ...failedExecutionReview.recipients,
                                  {
                                      ...emptyRecipientTraceability,
                                      id: "recipient-4",
                                      execution_id: "execution-0",
                                      campaign_id: "campaign-1",
                                      contact_id: "contact-4",
                                      contact_name: "Dana Dahl",
                                      email: "dana@example.com",
                                      phone: "+46700000003",
                                      first_name: "Dana",
                                      last_name: "Dahl",
                                      company: "Northwind",
                                      batch_number: 1,
                                      status: "failed" as const,
                                      failure_reason: "Mailbox unavailable",
                                      sent_at: null,
                                  },
                              ],
                          };
                }
                return latestExecutionReview;
            },
        );
        mocks.createMarketingExecutionFollowUpHandoff.mockResolvedValue({
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            requested_count: 2,
            created_count: 1,
            failed_count: 1,
            results: [
                {
                    recipient_id: "recipient-2",
                    contact_name: "Bjorn Berg",
                    email: "bjorn@example.com",
                    status: "created",
                    support_ticket_id: "ticket-1",
                    message: null,
                },
                {
                    recipient_id: "recipient-4",
                    contact_name: "Dana Dahl",
                    email: "dana@example.com",
                    status: "failed",
                    support_ticket_id: null,
                    message: "Contact does not exist in tenant scope.",
                },
            ],
        });

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));
        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));
        await waitFor(() => {
            expect(screen.getByLabelText("Select failed recipient Bjorn Berg")).toBeTruthy();
            expect(screen.getByLabelText("Select failed recipient Dana Dahl")).toBeTruthy();
        });

        fireEvent.click(screen.getByLabelText("Select failed recipient Bjorn Berg"));
        fireEvent.click(screen.getByLabelText("Select failed recipient Dana Dahl"));
        fireEvent.click(screen.getByRole("button", { name: /Create follow-up tasks/i }));
        fireEvent.click(screen.getByRole("button", { name: /Confirm follow-up handoff/i }));

        expect(
            await screen.findByText(
                /Created 1 follow-up task; 1 handoff failed. Dana Dahl: Contact does not exist in tenant scope./i,
            ),
        ).toBeTruthy();
    });

    it("shows duplicate handoff feedback explicitly when a failed recipient was already handed off", async () => {
        mocks.createMarketingExecutionFollowUpHandoff.mockResolvedValue({
            execution_id: "execution-0",
            campaign_id: "campaign-1",
            requested_count: 1,
            created_count: 0,
            failed_count: 1,
            results: [
                {
                    recipient_id: "recipient-2",
                    contact_name: "Bjorn Berg",
                    email: "bjorn@example.com",
                    status: "failed",
                    support_ticket_id: "ticket-1",
                    message: "already_handed_off",
                },
            ],
        });

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));
        await waitFor(() => {
            expect(screen.getByText("Execution execution-0")).toBeTruthy();
        });

        fireEvent.click(screen.getByText("Execution execution-0"));
        await waitFor(() => {
            expect(screen.getByLabelText("Select failed recipient Bjorn Berg")).toBeTruthy();
        });

        fireEvent.click(screen.getByLabelText("Select failed recipient Bjorn Berg"));
        fireEvent.click(screen.getByRole("button", { name: /Create follow-up tasks/i }));
        fireEvent.click(screen.getByRole("button", { name: /Confirm follow-up handoff/i }));

        expect(
            await screen.findByText(
                /Created 0 follow-up tasks; 1 handoff failed. Bjorn Berg: already_handed_off/i,
            ),
        ).toBeTruthy();
    });

    it("shows an empty follow-up state when no failed recipients are available", async () => {
        mocks.getMarketingCampaignExecutionDetail.mockResolvedValue({
            ...latestExecutionReview,
            recipient_counts: [
                { status: "all" as const, count: 1 },
                { status: "failed" as const, count: 0 },
                { status: "sent" as const, count: 0 },
                { status: "pending" as const, count: 1 },
                { status: "blocked" as const, count: 0 },
            ],
            recipients: [],
        });

        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /Spring launch/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /Spring launch/i }));

        expect(
            await screen.findByText(
                "No failed recipients are available in the current filtered view for follow-up handoff.",
            ),
        ).toBeTruthy();
        expect(screen.getByRole("button", { name: /Create follow-up tasks/i })).toHaveProperty(
            "disabled",
            true,
        );
    });

    it("creates a new company audience campaign draft", async () => {
        render(<MarketingCampaignsManager />);

        await waitFor(() => {
            expect(mocks.getMarketingCampaigns).toHaveBeenCalledTimes(1);
        });

        fireEvent.click(screen.getByRole("button", { name: /New draft/i }));
        fireEvent.change(screen.getByLabelText(/Campaign name/i), {
            target: { value: "Nordic launch" },
        });
        fireEvent.change(screen.getByLabelText(/Audience scope/i), {
            target: { value: "target_company_contacts" },
        });
        fireEvent.change(screen.getByLabelText(/Target company/i), {
            target: { value: "company-1" },
        });
        fireEvent.change(screen.getByLabelText(/Subject/i), {
            target: { value: "Launch update" },
        });
        fireEvent.change(screen.getByLabelText(/Message body/i), {
            target: { value: "Hello there" },
        });
        fireEvent.click(screen.getByRole("button", { name: /Create campaign/i }));

        await waitFor(() => {
            expect(mocks.createMarketingCampaign).toHaveBeenCalledWith(
                expect.objectContaining({
                    name: "Nordic launch",
                    audience_type: "target_company_contacts",
                    target_company_id: "company-1",
                }),
            );
        });
    });
});
