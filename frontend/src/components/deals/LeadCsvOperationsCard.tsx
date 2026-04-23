"use client";

import { useState } from "react";

import { triggerBrowserDownload } from "@/lib/download-file";
import { formatDealLabel } from "@/lib/deals";
import { getApiErrorMessage } from "@/lib/api-errors";
import { exportLeadsCsv, importLeadsCsv } from "@/services/deals.service";
import type { LeadImportResult } from "@/types/crm";

type LeadCsvOperationsCardProps = {
    exportQuery?: {
        q?: string;
        company_id?: string;
        contact_id?: string;
    };
};

export default function LeadCsvOperationsCard({
    exportQuery,
}: LeadCsvOperationsCardProps) {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [createMissingCompanies, setCreateMissingCompanies] = useState<boolean>(false);
    const [isImporting, setIsImporting] = useState<boolean>(false);
    const [isExporting, setIsExporting] = useState<boolean>(false);
    const [feedbackMessage, setFeedbackMessage] = useState<string>("");
    const [feedbackTone, setFeedbackTone] = useState<"success" | "error" | "info">("info");
    const [importResult, setImportResult] = useState<LeadImportResult | null>(null);

    async function handleImport(): Promise<void> {
        if (!selectedFile) {
            setFeedbackTone("error");
            setFeedbackMessage("Select a CSV file before starting the lead import.");
            return;
        }

        try {
            setIsImporting(true);
            setFeedbackMessage("");
            const csvText = await selectedFile.text();
            const result = await importLeadsCsv({
                csv_text: csvText,
                create_missing_companies: createMissingCompanies,
            });
            setImportResult(result);
            setFeedbackTone(result.error_rows > 0 ? "error" : "success");
            setFeedbackMessage(
                result.error_rows > 0
                    ? `Imported ${result.imported_rows} leads with ${result.error_rows} row errors.`
                    : `Imported ${result.imported_rows} leads successfully.`,
            );
        } catch (error) {
            setImportResult(null);
            setFeedbackTone("error");
            setFeedbackMessage(getApiErrorMessage(error, "The lead CSV could not be imported."));
        } finally {
            setIsImporting(false);
        }
    }

    async function handleExport(): Promise<void> {
        try {
            setIsExporting(true);
            setFeedbackMessage("");
            const download = await exportLeadsCsv(exportQuery);
            triggerBrowserDownload(download.blob, download.filename);
            setFeedbackTone("success");
            setFeedbackMessage(
                `Exported ${download.rowCount} lead${download.rowCount === 1 ? "" : "s"} to ${download.filename}.`,
            );
        } catch (error) {
            setFeedbackTone("error");
            setFeedbackMessage(getApiErrorMessage(error, "The lead export could not be generated."));
        } finally {
            setIsExporting(false);
        }
    }

    const feedbackClasses =
        feedbackTone === "error"
            ? "border-red-200 bg-red-50 text-red-700"
            : feedbackTone === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-slate-200 bg-slate-50 text-slate-700";

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h2 className="text-xl font-semibold text-slate-900">Lead CSV import and export</h2>
                    <p className="mt-1 text-sm text-slate-600">
                        Leads stay grounded in the existing sales deal workflow. This slice only imports active lead stages and exports lead-stage deals as CSV.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => {
                        void handleExport();
                    }}
                    disabled={isExporting}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {isExporting ? "Exporting..." : "Export leads CSV"}
                </button>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[1.3fr_auto] lg:items-end">
                <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="leads-csv-file">
                        Lead CSV file
                    </label>
                    <input
                        id="leads-csv-file"
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                        className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                    />
                    <p className="mt-2 text-xs text-slate-500">
                        Supported columns: `name`, `company`, `first_name`, `last_name`, `email`, `phone`, `amount`, `currency`, `stage`, `status`, `source`, `notes`
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => {
                        void handleImport();
                    }}
                    disabled={isImporting}
                    className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {isImporting ? "Importing..." : "Import leads CSV"}
                </button>
            </div>

            <label className="mt-4 flex items-start gap-3 text-sm text-slate-700">
                <input
                    type="checkbox"
                    checked={createMissingCompanies}
                    onChange={(event) => setCreateMissingCompanies(event.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300"
                />
                <span>Create tenant companies when a lead row references a company name that does not exist yet.</span>
            </label>

            {feedbackMessage ? (
                <div className={`mt-4 rounded-lg border px-4 py-3 text-sm ${feedbackClasses}`}>
                    {feedbackMessage}
                </div>
            ) : null}

            {importResult ? (
                <div className="mt-6">
                    <div className="flex flex-wrap gap-4 text-sm text-slate-600">
                        <span>Total rows: {importResult.total_rows}</span>
                        <span>Imported: {importResult.imported_rows}</span>
                        <span>Errors: {importResult.error_rows}</span>
                    </div>

                    {importResult.rows.length > 0 ? (
                        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200">
                            <table className="min-w-full divide-y divide-slate-200">
                                <thead className="bg-slate-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Row
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Lead
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Company
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Email
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Stage
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Result
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Message
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-200 bg-white">
                                    {importResult.rows.map((row) => (
                                        <tr key={`${row.row_number}-${row.name ?? row.company ?? "lead"}`}>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.row_number}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.name ?? "-"}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.company ?? "-"}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.email ?? "-"}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                {row.stage ? formatDealLabel(row.stage) : "-"}
                                            </td>
                                            <td className="px-4 py-3 text-sm">
                                                <span
                                                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                                                        row.result === "imported"
                                                            ? "bg-emerald-100 text-emerald-700"
                                                            : "bg-red-100 text-red-700"
                                                    }`}
                                                >
                                                    {row.result}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.message}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : null}
                </div>
            ) : null}
        </section>
    );
}
