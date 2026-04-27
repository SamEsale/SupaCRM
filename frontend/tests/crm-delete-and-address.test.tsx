import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import {
    buildCompanyAddress,
    formatCompanyAddress,
} from "@/components/crm/company-address-utils";
import CompanyCreateForm from "@/components/crm/company-create-form";

const mocks = vi.hoisted(() => ({
    getContacts: vi.fn(),
    getContactById: vi.fn(),
    deleteContact: vi.fn(),
    getCompanies: vi.fn(),
    getCompanyById: vi.fn(),
    deleteCompany: vi.fn(),
    getDeals: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
}));

let currentParams: Record<string, string> = {};

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mocks.push,
        refresh: mocks.refresh,
    }),
    useParams: () => currentParams,
}));

vi.mock("@/services/contacts.service", () => ({
    getContacts: mocks.getContacts,
    getContactById: mocks.getContactById,
    deleteContact: mocks.deleteContact,
}));

vi.mock("@/services/companies.service", () => ({
    createCompany: vi.fn(),
    getCompanies: mocks.getCompanies,
    getCompanyById: mocks.getCompanyById,
    deleteCompany: mocks.deleteCompany,
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
}));

import ContactDetailPage from "@/app/(dashboard)/contacts/[contactId]/page";
import ContactsPage from "@/app/(dashboard)/contacts/page";
import CompanyDetailPage from "@/app/(dashboard)/companies/[companyId]/page";
import CompaniesPage from "@/app/(dashboard)/companies/page";

function resetMocks(): void {
    currentParams = {};
    mocks.getContacts.mockReset();
    mocks.getContactById.mockReset();
    mocks.deleteContact.mockReset();
    mocks.getCompanies.mockReset();
    mocks.getCompanyById.mockReset();
    mocks.deleteCompany.mockReset();
    mocks.getDeals.mockReset();
    mocks.push.mockReset();
    mocks.refresh.mockReset();
    vi.spyOn(window, "confirm").mockReturnValue(true);
}

beforeEach(() => {
    resetMocks();
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe("CRM delete actions and company address fields", () => {
    it("deletes a contact from the contacts list and refreshes the list", async () => {
        mocks.getContacts
            .mockResolvedValueOnce({
                items: [
                    {
                        id: "contact-1",
                        tenant_id: "tenant-1",
                        first_name: "Ada",
                        last_name: "Lovelace",
                        email: "ada@example.com",
                        phone: null,
                        company_id: null,
                        company: null,
                        job_title: null,
                        notes: null,
                        created_at: "2026-01-01T00:00:00.000Z",
                        updated_at: "2026-01-01T00:00:00.000Z",
                    },
                ],
                total: 1,
            })
            .mockResolvedValueOnce({
                items: [],
                total: 0,
            });

        mocks.deleteContact.mockResolvedValue({ success: true, message: "Contact deleted successfully" });

        render(<ContactsPage />);

        await waitFor(() => {
            expect(mocks.getContacts).toHaveBeenCalledTimes(1);
            expect(screen.getByText("Ada Lovelace")).toBeTruthy();
            expect(screen.getByRole("columnheader", { name: /actions/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /delete contact/i }));

        await waitFor(() => {
            expect(mocks.deleteContact).toHaveBeenCalledWith("contact-1");
            expect(mocks.getContacts).toHaveBeenCalledTimes(2);
        });
    });

    it("exposes a real add lead entry point from the contacts page", async () => {
        mocks.getContacts.mockResolvedValue({
            items: [],
            total: 0,
        });

        render(<ContactsPage />);

        await waitFor(() => {
            expect(mocks.getContacts).toHaveBeenCalledTimes(1);
        });

        expect(screen.getByRole("link", { name: /^add lead$/i }).getAttribute("href")).toBe("/sales/leads/create");
    });

    it("deletes a company from the companies list and refreshes the list", async () => {
        mocks.getCompanies
            .mockResolvedValueOnce({
                items: [
                    {
                        id: "company-1",
                        tenant_id: "tenant-1",
                        name: "Acme Inc",
                        website: null,
                        email: null,
                        phone: null,
                        industry: null,
                        address: null,
                        vat_number: null,
                        registration_number: null,
                        notes: null,
                        created_at: "2026-01-01T00:00:00.000Z",
                        updated_at: "2026-01-01T00:00:00.000Z",
                    },
                ],
                total: 1,
            })
            .mockResolvedValueOnce({
                items: [],
                total: 0,
            });

        mocks.deleteCompany.mockResolvedValue({ success: true, message: "Company deleted successfully" });

        render(<CompaniesPage />);

        await waitFor(() => {
            expect(mocks.getCompanies).toHaveBeenCalledTimes(1);
            expect(screen.getByText("Acme Inc")).toBeTruthy();
            expect(screen.getByRole("columnheader", { name: /actions/i })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /delete company/i }));

        await waitFor(() => {
            expect(mocks.deleteCompany).toHaveBeenCalledWith("company-1");
            expect(mocks.getCompanies).toHaveBeenCalledTimes(2);
        });
    });

    it("redirects to the contacts list after deleting from the contact detail page", async () => {
        currentParams = { contactId: "contact-1" };
        mocks.getContactById.mockResolvedValue({
            id: "contact-1",
            tenant_id: "tenant-1",
            first_name: "Ada",
            last_name: "Lovelace",
            email: "ada@example.com",
            phone: null,
            company_id: null,
            company: null,
            job_title: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getDeals.mockResolvedValue({ items: [], total: 0 });
        mocks.deleteContact.mockResolvedValue({ success: true, message: "Contact deleted successfully" });

        render(<ContactDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Ada Lovelace" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /delete contact/i }));

        await waitFor(() => {
            expect(mocks.deleteContact).toHaveBeenCalledWith("contact-1");
            expect(mocks.push).toHaveBeenCalledWith("/contacts");
            expect(mocks.refresh).toHaveBeenCalled();
        });
    });

    it("builds a create lead handoff from the contact detail page", async () => {
        currentParams = { contactId: "contact-1" };
        mocks.getContactById.mockResolvedValue({
            id: "contact-1",
            tenant_id: "tenant-1",
            first_name: "Ada",
            last_name: "Lovelace",
            email: "ada@example.com",
            phone: "+46 555 010 100",
            company_id: "company-1",
            company: "Acme Inc",
            job_title: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getCompanyById.mockResolvedValue({
            id: "company-1",
            tenant_id: "tenant-1",
            name: "Acme Inc",
            website: null,
            email: null,
            phone: null,
            industry: null,
            address: null,
            vat_number: null,
            registration_number: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getDeals.mockResolvedValue({
            items: [
                {
                    id: "deal-1",
                    tenant_id: "tenant-1",
                    name: "Expansion Deal",
                    company_id: "company-1",
                    contact_id: "contact-1",
                    product_id: null,
                    amount: "1500.00",
                    currency: "USD",
                    stage: "new lead",
                    status: "open",
                    expected_close_date: null,
                    notes: null,
                    next_follow_up_at: null,
                    follow_up_note: null,
                    closed_at: null,
                    created_at: "2026-01-01T00:00:00.000Z",
                    updated_at: "2026-01-01T00:00:00.000Z",
                },
            ],
            total: 1,
        });

        render(<ContactDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Ada Lovelace" })).toBeTruthy();
        });

        expect(screen.getByRole("link", { name: /^create lead$/i }).getAttribute("href")).toBe(
            "/sales/leads/create?company_id=company-1&contact_id=contact-1",
        );
        expect(screen.getByText(/New Lead · \$1,500\.00 · Open/i)).toBeTruthy();
    });

    it("redirects to the companies list after deleting from the company detail page", async () => {
        currentParams = { companyId: "company-1" };
        mocks.getCompanyById.mockResolvedValue({
            id: "company-1",
            tenant_id: "tenant-1",
            name: "Acme Inc",
            website: null,
            email: null,
            phone: null,
            industry: null,
            address: null,
            vat_number: null,
            registration_number: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getContacts.mockResolvedValue({ items: [], total: 0 });
        mocks.getDeals.mockResolvedValue({ items: [], total: 0 });
        mocks.deleteCompany.mockResolvedValue({ success: true, message: "Company deleted successfully" });

        render(<CompanyDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Acme Inc" })).toBeTruthy();
        });

        fireEvent.click(screen.getByRole("button", { name: /delete company/i }));

        await waitFor(() => {
            expect(mocks.deleteCompany).toHaveBeenCalledWith("company-1");
            expect(mocks.push).toHaveBeenCalledWith("/companies");
            expect(mocks.refresh).toHaveBeenCalled();
        });
    });

    it("builds a create lead handoff from the company detail page", async () => {
        currentParams = { companyId: "company-1" };
        mocks.getCompanyById.mockResolvedValue({
            id: "company-1",
            tenant_id: "tenant-1",
            name: "Acme Inc",
            website: null,
            email: null,
            phone: null,
            industry: null,
            address: null,
            vat_number: null,
            registration_number: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getContacts.mockResolvedValue({ items: [], total: 0 });
        mocks.getDeals.mockResolvedValue({
            items: [
                {
                    id: "deal-1",
                    tenant_id: "tenant-1",
                    name: "Expansion Deal",
                    company_id: "company-1",
                    contact_id: null,
                    product_id: null,
                    amount: "2500.00",
                    currency: "USD",
                    stage: "qualified lead",
                    status: "in progress",
                    expected_close_date: null,
                    notes: null,
                    next_follow_up_at: null,
                    follow_up_note: null,
                    closed_at: null,
                    created_at: "2026-01-01T00:00:00.000Z",
                    updated_at: "2026-01-01T00:00:00.000Z",
                },
            ],
            total: 1,
        });

        render(<CompanyDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Acme Inc" })).toBeTruthy();
        });

        expect(screen.getByRole("link", { name: /^create lead$/i }).getAttribute("href")).toBe(
            "/sales/leads/create?company_id=company-1",
        );
        expect(screen.getByText(/Qualified Lead · \$2,500\.00 · In Progress/i)).toBeTruthy();
    });

    it("renders a formatted comma-separated company address on the company detail page", async () => {
        currentParams = { companyId: "company-1" };
        const storedAddress = buildCompanyAddress({
            street: "asdasdas",
            unit: "41",
            postalCode: "15451",
            city: "cluj",
            stateCounty: "cluj",
            country: "Central African Republic",
        });

        mocks.getCompanyById.mockResolvedValue({
            id: "company-1",
            tenant_id: "tenant-1",
            name: "Acme Inc",
            website: null,
            email: null,
            phone: null,
            industry: null,
            address: storedAddress,
            vat_number: null,
            registration_number: null,
            notes: null,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
        });
        mocks.getContacts.mockResolvedValue({ items: [], total: 0 });
        mocks.getDeals.mockResolvedValue({ items: [], total: 0 });

        render(<CompanyDetailPage />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Acme Inc" })).toBeTruthy();
        });

        const expectedAddress = formatCompanyAddress(storedAddress);
        expect(screen.getByText(expectedAddress)).toBeTruthy();
    });

    it("omits empty company address parts without malformed commas", () => {
        expect(
            formatCompanyAddress(
                buildCompanyAddress({
                    street: "Main Street 1",
                    unit: "",
                    postalCode: "",
                    city: "Stockholm",
                    stateCounty: "",
                    country: "Sweden",
                }),
            ),
        ).toBe("Main Street 1, Stockholm, Sweden");
    });

    it("renders state/county as text input and country as a dropdown after it", async () => {
        render(<CompanyCreateForm />);

        const stateCountyInput = screen.getByLabelText(/^State \/ County$/i);
        const countrySelect = screen.getByLabelText(/^Country$/i);

        expect(stateCountyInput.tagName).toBe("INPUT");
        expect(countrySelect.tagName).toBe("SELECT");
        expect(
            stateCountyInput.compareDocumentPosition(countrySelect) &
                Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
    });

    it("renders a broad UN-style country list with representative entries", () => {
        render(<CompanyCreateForm />);

        const countrySelect = screen.getByLabelText(/^Country$/i) as HTMLSelectElement;
        const optionValues = Array.from(countrySelect.options).map((option) => option.value);

        expect(optionValues.length).toBeGreaterThan(150);
        expect(optionValues).toContain("United States");
        expect(optionValues).toContain("Sweden");
        expect(optionValues).toContain("Japan");
        expect(optionValues).toContain("South Africa");
    });

    it("submits the typed state/county and selected country in the address payload", async () => {
        const onSubmit = vi.fn().mockResolvedValue(undefined);

        render(<CompanyCreateForm onSubmit={onSubmit} />);

        fireEvent.change(screen.getByPlaceholderText(/company name/i), {
            target: { value: "Acme Inc" },
        });
        fireEvent.change(screen.getByPlaceholderText(/^Street$/i), {
            target: { value: "Main Street 1" },
        });
        fireEvent.change(screen.getByPlaceholderText(/^Postal$/i), {
            target: { value: "12345" },
        });
        fireEvent.change(screen.getByPlaceholderText(/^City$/i), {
            target: { value: "Stockholm" },
        });
        fireEvent.change(screen.getByLabelText(/^State \/ County$/i), {
            target: { value: "Stockholm County" },
        });
        fireEvent.change(screen.getByLabelText(/^Country$/i), {
            target: { value: "Sweden" },
        });

        fireEvent.click(screen.getByRole("button", { name: /create company/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(
            expect.objectContaining({
                name: "Acme Inc",
            }),
        );

        const submitted = onSubmit.mock.calls[0][0] as { address: string | null };
        expect(submitted.address).toContain("Stockholm County");
        expect(submitted.address).toContain("Sweden");
    });

    it("prefills the country and state/county selects from an existing structured address", () => {
        render(
            <CompanyCreateForm
                mode="edit"
                initialValues={{
                    name: "Acme Inc",
                    address: buildCompanyAddress({
                        street: "Main Street 1",
                        unit: "",
                        postalCode: "12345",
                        city: "Stockholm",
                        stateCounty: "Stockholm County",
                        country: "Sweden",
                    }),
                }}
            />,
        );
        expect((screen.getByLabelText(/^State \/ County$/i) as HTMLInputElement).value).toBe(
            "Stockholm County",
        );
        expect((screen.getByLabelText(/^Country$/i) as HTMLSelectElement).value).toBe("Sweden");
    });
});
