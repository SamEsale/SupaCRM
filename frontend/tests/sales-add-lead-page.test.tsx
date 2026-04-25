import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getCompanies: vi.fn(),
    getContacts: vi.fn(),
    createLead: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    searchParams: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
    useSearchParams: () => mocks.searchParams,
}));

vi.mock("@/services/companies.service", () => ({
    getCompanies: mocks.getCompanies,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
}));

vi.mock("@/services/deals.service", () => ({
    createLead: mocks.createLead,
}));

import CreateLeadPage from "@/app/(dashboard)/sales/leads/create/page";

describe("sales add lead page", () => {
    beforeEach(() => {
        mocks.getCompanies.mockReset();
        mocks.getContacts.mockReset();
        mocks.createLead.mockReset();
        mocks.push.mockReset();
        mocks.refresh.mockReset();
        mocks.searchParams = new URLSearchParams();

        mocks.getCompanies.mockResolvedValue({
            items: [
                {
                    id: "company-1",
                    tenant_id: "tenant-1",
                    name: "Northwind Labs",
                    website: null,
                    email: null,
                    phone: null,
                    industry: null,
                    address: null,
                    vat_number: null,
                    registration_number: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.getContacts.mockResolvedValue({
            items: [
                {
                    id: "contact-1",
                    tenant_id: "tenant-1",
                    first_name: "Alex",
                    last_name: "Admin",
                    email: "alex@example.com",
                    phone: "+46 555 010 101",
                    company_id: "company-1",
                    company: "Northwind Labs",
                    job_title: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 1,
        });
        mocks.createLead.mockResolvedValue({
            id: "deal-1",
            tenant_id: "tenant-1",
            name: "Website expansion",
            company_id: "company-1",
            contact_id: "contact-1",
            product_id: null,
            amount: "1200.00",
            currency: "USD",
            stage: "new lead",
            status: "open",
            expected_close_date: null,
            notes: "Lead source: website",
            next_follow_up_at: null,
            follow_up_note: null,
            closed_at: null,
            created_at: "2026-04-10T10:00:00.000Z",
            updated_at: "2026-04-10T10:00:00.000Z",
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("creates a lead through the deal-backed sales flow and routes to the new deal", async () => {
        render(<CreateLeadPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Add Lead" })).toBeTruthy();
            expect(screen.getByLabelText(/^Lead name$/i)).toBeTruthy();
        });

        fireEvent.change(screen.getByLabelText(/^Lead name$/i), {
            target: { value: "Website expansion" },
        });
        fireEvent.change(screen.getByLabelText(/^Company$/i), {
            target: { value: "company-1" },
        });
        fireEvent.change(screen.getByLabelText(/^Contact$/i), {
            target: { value: "contact-1" },
        });
        fireEvent.change(screen.getByLabelText(/^Source$/i), {
            target: { value: "website" },
        });
        fireEvent.change(screen.getByLabelText(/^Email$/i), {
            target: { value: "lead@example.com" },
        });
        fireEvent.change(screen.getByLabelText(/^Phone$/i), {
            target: { value: "+46 555 010 101" },
        });
        fireEvent.change(screen.getByLabelText(/^Amount$/i), {
            target: { value: "1200" },
        });
        fireEvent.change(screen.getByLabelText(/^Currency$/i), {
            target: { value: "usd" },
        });
        fireEvent.change(screen.getByLabelText(/^Notes$/i), {
            target: { value: "Qualified from the website contact form." },
        });

        fireEvent.click(screen.getByRole("button", { name: /create lead/i }));

        await waitFor(() => {
            expect(mocks.createLead).toHaveBeenCalledWith({
                name: "Website expansion",
                company_id: "company-1",
                contact_id: "contact-1",
                email: "lead@example.com",
                phone: "+46 555 010 101",
                amount: "1200",
                currency: "USD",
                source: "website",
                notes: "Qualified from the website contact form.",
            });
        });

        await waitFor(() => {
            expect(mocks.push).toHaveBeenCalledWith("/deals/deal-1?createdFrom=lead-intake");
            expect(mocks.refresh).toHaveBeenCalled();
        });
    });

    it("prefills the lead form from grounded query-string context", async () => {
        mocks.searchParams = new URLSearchParams({
            source: "whatsapp",
            name: "WhatsApp lead",
            phone: "+46 555 010 102",
            message: "Need pricing for onboarding",
            campaign: "Spring launch",
        });

        render(<CreateLeadPage />);

        await waitFor(() => {
            expect(screen.getByLabelText(/^Lead name$/i)).toBeTruthy();
        });

        expect((screen.getByLabelText(/^Lead name$/i) as HTMLInputElement).value).toBe("WhatsApp lead");
        expect((screen.getByLabelText(/^Phone$/i) as HTMLInputElement).value).toBe("+46 555 010 102");
        expect((screen.getByLabelText(/^Source$/i) as HTMLSelectElement).value).toBe("whatsapp");
        expect((screen.getByLabelText(/^Notes$/i) as HTMLTextAreaElement).value).toContain("Need pricing for onboarding");
        expect((screen.getByLabelText(/^Notes$/i) as HTMLTextAreaElement).value).toContain("Campaign: Spring launch");
    });

    it("prefills the lead form from contact and company query context", async () => {
        mocks.searchParams = new URLSearchParams({
            company_id: "company-1",
            contact_id: "contact-1",
        });

        render(<CreateLeadPage />);

        await waitFor(() => {
            expect(screen.getByLabelText(/^Lead name$/i)).toBeTruthy();
        });

        expect((screen.getByLabelText(/^Lead name$/i) as HTMLInputElement).value).toBe("Alex Admin");
        expect((screen.getByLabelText(/^Company$/i) as HTMLSelectElement).value).toBe("company-1");
        expect((screen.getByLabelText(/^Contact$/i) as HTMLSelectElement).value).toBe("contact-1");
        expect((screen.getByLabelText(/^Email$/i) as HTMLInputElement).value).toBe("alex@example.com");
        expect((screen.getByLabelText(/^Phone$/i) as HTMLInputElement).value).toBe("+46 555 010 101");
        expect(screen.getByText(/Starting from a contact record/i)).toBeTruthy();
    });

    it("rejects mismatched contact and company query params safely", async () => {
        mocks.getCompanies.mockResolvedValue({
            items: [
                {
                    id: "company-1",
                    tenant_id: "tenant-1",
                    name: "Northwind Labs",
                    website: null,
                    email: null,
                    phone: null,
                    industry: null,
                    address: null,
                    vat_number: null,
                    registration_number: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
                {
                    id: "company-2",
                    tenant_id: "tenant-1",
                    name: "Tailspin Toys",
                    website: null,
                    email: null,
                    phone: null,
                    industry: null,
                    address: null,
                    vat_number: null,
                    registration_number: null,
                    notes: null,
                    created_at: "2026-04-01T10:00:00.000Z",
                    updated_at: "2026-04-01T10:00:00.000Z",
                },
            ],
            total: 2,
        });
        mocks.searchParams = new URLSearchParams({
            company_id: "company-2",
            contact_id: "contact-1",
        });

        render(<CreateLeadPage />);

        await waitFor(() => {
            expect(screen.getByText(/selected contact does not belong to the selected company/i)).toBeTruthy();
        });

        expect(screen.queryByLabelText(/^Lead name$/i)).toBeNull();
    });
});
