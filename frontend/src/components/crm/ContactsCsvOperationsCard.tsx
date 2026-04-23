"use client";

import { useState } from "react";

import { triggerBrowserDownload } from "@/lib/download-file";
import { getApiErrorMessage } from "@/lib/api-errors";
import { exportContactsCsv, importContactsCsv } from "@/services/contacts.service";
import type { ContactImportResult } from "@/types/crm";

type ContactsCsvOperationsCardProps = {
    exportQuery?: {
        q?: string;
        company_id?: string;
    };
};

export default function ContactsCsvOperationsCard({
    exportQuery,
}: ContactsCsvOperationsCardProps) {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [createMissingCompanies, setCreateMissingCompanies] = useState<boolean>(false);
    const [isImporting, setIsImporting] = useState<boolean>(false);
    const [isExporting, setIsExporting] = useState<boolean>(false);
    const [feedbackMessage, setFeedbackMessage] = useState<string>("");
    const [feedbackTone, setFeedbackTone] = useState<"success" | "error" | "info">("info");
    const [importResult, setImportResult] = useState<ContactImportResult | null>(null);

    async function handleImport(): Promise<void> {
        if (!selectedFile) {
            setFeedbackTone("error");
            setFeedbackMessage("Select a CSV file before starting the contact import.");
            return;
        }

        try {
            setIsImporting(true);
            setFeedbackMessage("");
            const csvText = await selectedFile.text();
            const result = await importContactsCsv({
                csv_text: csvText,
                create_missing_companies: createMissingCompanies,
            });
            setImportResult(result);
            setFeedbackTone(result.error_rows > 0 ? "error" : "success");
            setFeedbackMessage(
                result.error_rows > 0
                    ? `Imported ${result.imported_rows} contacts with ${result.error_rows} row errors.`
                    : `Imported ${result.imported_rows} contacts successfully.`,
            );
        } catch (error) {
            setImportResult(null);
            setFeedbackTone("error");
            setFeedbackMessage(
                getApiErrorMessage(error, "The contact CSV could not be imported."),
            );
        } finally {
            setIsImporting(false);
        }
    }

    async function handleExport(): Promise<void> {
        try {
            setIsExporting(true);
            setFeedbackMessage("");
            const download = await exportContactsCsv(exportQuery);
            triggerBrowserDownload(download.blob, download.filename);
            setFeedbackTone("success");
            setFeedbackMessage(
                `Exported ${download.rowCount} contact${download.rowCount === 1 ? "" : "s"} to ${download.filename}.`,
            );
        } catch (error) {
            setFeedbackTone("error");
            setFeedbackMessage(
                getApiErrorMessage(error, "The contact export could not be generated."),
            );
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
                    <h2 className="text-xl font-semibold text-slate-900">Contact CSV import and export</h2>
                    <p className="mt-1 text-sm text-slate-600">
                        Launch scope is CSV only. Imports write directly into tenant contacts and exports stay ready for bulk audience preparation.
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
                    {isExporting ? "Exporting..." : "Export contacts CSV"}
                </button>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[1.3fr_auto] lg:items-end">
                <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="contacts-csv-file">
                        Contact CSV file
                    </label>
                    <input
                        id="contacts-csv-file"
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                        className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                    />
                    <p className="mt-2 text-xs text-slate-500">
                        Supported columns: `first_name`, `last_name`, `email`, `phone`, `company`, `job_title`, `notes`
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
                    {isImporting ? "Importing..." : "Import contacts CSV"}
                </button>
            </div>

            <label className="mt-4 flex items-start gap-3 text-sm text-slate-700">
                <input
                    type="checkbox"
                    checked={createMissingCompanies}
                    onChange={(event) => setCreateMissingCompanies(event.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300"
                />
                <span>Create tenant companies when a row references a company name that does not exist yet.</span>
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
                                            Contact
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Email
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                            Company
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
                                        <tr key={`${row.row_number}-${row.email ?? row.first_name ?? "contact"}`}>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.row_number}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">
                                                {[row.first_name, row.last_name].filter(Boolean).join(" ") || "-"}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.email ?? "-"}</td>
                                            <td className="px-4 py-3 text-sm text-slate-700">{row.company ?? "-"}</td>
                                            <td className="px-4 py-3 text-sm">
                                                <span
                                                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                                                        row.status === "imported"
                                                            ? "bg-emerald-100 text-emerald-700"
                                                            : "bg-red-100 text-red-700"
                                                    }`}
                                                >
                                                    {row.status}
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
