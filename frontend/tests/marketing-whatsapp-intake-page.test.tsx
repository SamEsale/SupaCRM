import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const routerMocks = vi.hoisted(() => ({
    push: vi.fn(),
    refresh: vi.fn(),
}));

const serviceMocks = vi.hoisted(() => ({
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    getMarketingCampaigns: vi.fn(),
    createWhatsAppLeadIntake: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => routerMocks,
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: serviceMocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: serviceMocks.getContacts,
}));

vi.mock("@/services/marketing.service", () => ({
    getMarketingCampaigns: serviceMocks.getMarketingCampaigns,
    createWhatsAppLeadIntake: serviceMocks.createWhatsAppLeadIntake,
}));

import WhatsAppLeadIntakeForm from "@/components/marketing/WhatsAppLeadIntakeForm";

beforeEach(() => {
    routerMocks.push.mockReset();
    routerMocks.refresh.mockReset();
    serviceMocks.getCompanies.mockReset();
    serviceMocks.getContacts.mockReset();
    serviceMocks.getMarketingCampaigns.mockReset();
    serviceMocks.createWhatsAppLeadIntake.mockReset();

    serviceMocks.getCompanies.mockResolvedValue({ items: [], total: 0 });
    serviceMocks.getContacts.mockResolvedValue({ items: [], total: 0 });
    serviceMocks.getMarketingCampaigns.mockResolvedValue({
        items: [
            {
                id: "campaign-1",
                tenant_id: "tenant-1",
                name: "WhatsApp revive",
                channel: "whatsapp",
                audience_type: "all_contacts",
                audience_description: "Dormant buyers",
                target_company_id: null,
                target_contact_id: null,
                subject: null,
                message_body: "Hi again",
                status: "draft",
                scheduled_for: null,
                created_at: "2026-04-12T10:00:00Z",
                updated_at: "2026-04-12T10:00:00Z",
            },
        ],
        total: 1,
    });
    serviceMocks.createWhatsAppLeadIntake.mockResolvedValue({
        deal: { id: "deal-1", label: "WhatsApp Lead - Alicia" },
        company: { id: "company-1", label: "Northwind" },
        contact: { id: "contact-1", label: "Alicia Andersson" },
        campaign: { id: "campaign-1", label: "WhatsApp revive" },
    });
});

afterEach(() => {
    cleanup();
});

describe("whatsapp lead intake", () => {
    it("keeps the intake workspace usable when campaign drafts are unavailable", async () => {
        serviceMocks.getMarketingCampaigns.mockRejectedValueOnce({
            response: {
                status: 404,
                data: {
                    detail: "Not found",
                },
            },
        });

        render(<WhatsAppLeadIntakeForm />);

        await waitFor(() => {
            expect(
                screen.getByText(
                    "WhatsApp campaign drafts are currently unavailable, but you can still capture and convert the lead.",
                ),
            ).toBeTruthy();
        });

        expect(screen.getByLabelText(/Contact name/i)).toBeTruthy();
        expect(screen.queryByText("The WhatsApp intake workspace could not be loaded from the backend.")).toBeNull();
    });

    it("submits intake context and routes into the deal detail flow", async () => {
        render(<WhatsAppLeadIntakeForm />);

        await waitFor(() => {
            expect(serviceMocks.getMarketingCampaigns).toHaveBeenCalledTimes(1);
        });

        fireEvent.change(screen.getByLabelText(/Contact name/i), {
            target: { value: "Alicia Andersson" },
        });
        fireEvent.change(screen.getByLabelText(/^Phone$/i), {
            target: { value: "+46700000000" },
        });
        fireEvent.change(screen.getByLabelText(/Or new company name/i), {
            target: { value: "Northwind" },
        });
        fireEvent.change(screen.getByLabelText(/WhatsApp campaign/i), {
            target: { value: "campaign-1" },
        });
        fireEvent.change(screen.getByLabelText(/Message content/i), {
            target: { value: "Can you send pricing?" },
        });
        fireEvent.change(screen.getByLabelText(/Qualification notes/i), {
            target: { value: "Hot lead from WhatsApp" },
        });
        fireEvent.click(screen.getByRole("button", { name: /Create WhatsApp lead/i }));

        await waitFor(() => {
            expect(serviceMocks.createWhatsAppLeadIntake).toHaveBeenCalledWith(
                expect.objectContaining({
                    sender_name: "Alicia Andersson",
                    sender_phone: "+46700000000",
                    company_name: "Northwind",
                    campaign_id: "campaign-1",
                    message_text: "Can you send pricing?",
                    notes: "Hot lead from WhatsApp",
                    currency: "USD",
                }),
            );
        });

        await waitFor(() => {
            expect(routerMocks.push).toHaveBeenCalledWith("/deals/deal-1?createdFrom=whatsapp-intake");
        });
        expect(routerMocks.refresh).toHaveBeenCalledTimes(1);
    });
});
