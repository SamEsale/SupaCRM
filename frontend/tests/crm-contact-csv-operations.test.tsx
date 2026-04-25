import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    importContactsCsv: vi.fn(),
    exportContactsCsv: vi.fn(),
    triggerBrowserDownload: vi.fn(),
}));

vi.mock("@/services/contacts.service", () => ({
    importContactsCsv: mocks.importContactsCsv,
    exportContactsCsv: mocks.exportContactsCsv,
}));

vi.mock("@/lib/download-file", () => ({
    triggerBrowserDownload: mocks.triggerBrowserDownload,
}));

import ContactsCsvOperationsCard from "@/components/crm/ContactsCsvOperationsCard";

describe("contact csv operations", () => {
    beforeEach(() => {
        mocks.importContactsCsv.mockReset();
        mocks.exportContactsCsv.mockReset();
        mocks.triggerBrowserDownload.mockReset();
    });

    afterEach(() => {
        cleanup();
    });

    it("imports a contact CSV and renders row-level results", async () => {
        mocks.importContactsCsv.mockResolvedValue({
            total_rows: 2,
            imported_rows: 1,
            error_rows: 1,
            rows: [
                {
                    row_number: 2,
                    first_name: "Ada",
                    last_name: "Lovelace",
                    email: "ada@example.com",
                    company: "Northwind",
                    status: "imported",
                    message: "Imported successfully.",
                },
                {
                    row_number: 3,
                    first_name: null,
                    last_name: "Missing",
                    email: "missing@example.com",
                    company: null,
                    status: "error",
                    message: "first_name is required",
                },
            ],
        });

        render(<ContactsCsvOperationsCard exportQuery={{ q: "ada" }} />);

        const file = new File(
            ["first_name,last_name,email\nAda,Lovelace,ada@example.com\n,Missing,missing@example.com\n"],
            "contacts.csv",
            { type: "text/csv" },
        );

        fireEvent.change(screen.getByLabelText(/contact csv file/i), {
            target: { files: [file] },
        });
        fireEvent.click(screen.getByRole("button", { name: /import contacts csv/i }));

        await waitFor(() => {
            expect(mocks.importContactsCsv).toHaveBeenCalledWith({
                csv_text: expect.stringContaining("Ada,Lovelace"),
                create_missing_companies: false,
            });
        });

        expect(screen.getByText(/Imported 1 contacts with 1 row errors/i)).toBeTruthy();
        expect(screen.getByText("Ada Lovelace")).toBeTruthy();
        expect(screen.getByText("first_name is required")).toBeTruthy();
    });

    it("exports contacts and shows success feedback", async () => {
        mocks.exportContactsCsv.mockResolvedValue({
            blob: new Blob(["csv"], { type: "text/csv" }),
            filename: "contacts-export.csv",
            rowCount: 3,
        });

        render(<ContactsCsvOperationsCard exportQuery={{ q: "northwind" }} />);

        fireEvent.click(screen.getByRole("button", { name: /export contacts csv/i }));

        await waitFor(() => {
            expect(mocks.exportContactsCsv).toHaveBeenCalledWith({ q: "northwind" });
            expect(mocks.triggerBrowserDownload).toHaveBeenCalled();
        });

        expect(screen.getByText(/Exported 3 contacts to contacts-export.csv/i)).toBeTruthy();
    });
});
