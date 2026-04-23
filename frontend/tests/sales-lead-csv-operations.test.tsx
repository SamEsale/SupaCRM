import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    importLeadsCsv: vi.fn(),
    exportLeadsCsv: vi.fn(),
    triggerBrowserDownload: vi.fn(),
}));

vi.mock("@/services/deals.service", () => ({
    importLeadsCsv: mocks.importLeadsCsv,
    exportLeadsCsv: mocks.exportLeadsCsv,
}));

vi.mock("@/lib/download-file", () => ({
    triggerBrowserDownload: mocks.triggerBrowserDownload,
}));

import LeadCsvOperationsCard from "@/components/deals/LeadCsvOperationsCard";

describe("lead csv operations", () => {
    beforeEach(() => {
        mocks.importLeadsCsv.mockReset();
        mocks.exportLeadsCsv.mockReset();
        mocks.triggerBrowserDownload.mockReset();
    });

    afterEach(() => {
        cleanup();
    });

    it("imports leads and exposes row-level validation feedback", async () => {
        mocks.importLeadsCsv.mockResolvedValue({
            total_rows: 2,
            imported_rows: 1,
            error_rows: 1,
            rows: [
                {
                    row_number: 2,
                    name: "Spring Outreach",
                    company: "Northwind",
                    email: "alicia@example.com",
                    stage: "qualified lead",
                    status: "open",
                    result: "imported",
                    message: "Imported successfully.",
                },
                {
                    row_number: 3,
                    name: "Closed Revenue",
                    company: "Northwind",
                    email: "finance@example.com",
                    stage: "contract signed",
                    status: "won",
                    result: "error",
                    message: "Lead imports only support the stages: new lead, qualified lead",
                },
            ],
        });

        render(<LeadCsvOperationsCard exportQuery={{ company_id: "company-1" }} />);

        const file = new File(
            ["name,company,stage,status\nSpring Outreach,Northwind,qualified lead,open\n"],
            "leads.csv",
            { type: "text/csv" },
        );

        fireEvent.change(screen.getByLabelText(/lead csv file/i), {
            target: { files: [file] },
        });
        fireEvent.click(screen.getByRole("button", { name: /import leads csv/i }));

        await waitFor(() => {
            expect(mocks.importLeadsCsv).toHaveBeenCalledWith({
                csv_text: expect.stringContaining("Spring Outreach"),
                create_missing_companies: false,
            });
        });

        expect(screen.getByText(/Imported 1 leads with 1 row errors/i)).toBeTruthy();
        expect(screen.getByText("Spring Outreach")).toBeTruthy();
        expect(screen.getByText(/Lead imports only support the stages/i)).toBeTruthy();
    });

    it("exports leads and reports completion", async () => {
        mocks.exportLeadsCsv.mockResolvedValue({
            blob: new Blob(["csv"], { type: "text/csv" }),
            filename: "leads-export.csv",
            rowCount: 2,
        });

        render(<LeadCsvOperationsCard exportQuery={{ q: "renewal", company_id: "company-1" }} />);

        fireEvent.click(screen.getByRole("button", { name: /export leads csv/i }));

        await waitFor(() => {
            expect(mocks.exportLeadsCsv).toHaveBeenCalledWith({
                q: "renewal",
                company_id: "company-1",
            });
            expect(mocks.triggerBrowserDownload).toHaveBeenCalled();
        });

        expect(screen.getByText(/Exported 2 leads to leads-export.csv/i)).toBeTruthy();
    });
});
