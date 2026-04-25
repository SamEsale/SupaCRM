import Link from "next/link";

import { formatCompanyAddress } from "@/components/crm/company-address-utils";
import type { Company } from "@/types/crm";

interface CompaniesListProps {
    companies: Company[];
    total: number;
    onDeleteCompany?: (company: Company) => void;
}

function formatPhone(phone: string | null): string {
    if (!phone) {
        return "-";
    }

    return phone.replace(/-/g, "");
}

export default function CompaniesList({
    companies,
    total,
    onDeleteCompany,
}: CompaniesListProps) {
    return (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Companies</h2>
                <p className="mt-1 text-sm text-slate-600">
                    {total} compan{total === 1 ? "y" : "ies"} loaded from the backend API.
                </p>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Address
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                VAT Number
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Registration Number
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Website
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Email
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Phone
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Industry
                            </th>
                            {onDeleteCompany ? (
                                <th className="sticky right-0 z-10 bg-slate-50 px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                    Actions
                                </th>
                            ) : null}
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200 bg-white">
                        {companies.map((company) => (
                            <tr key={company.id}>
                                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                                    <Link
                                        href={`/companies/${company.id}`}
                                        className="underline-offset-2 hover:underline"
                                    >
                                        {company.name}
                                    </Link>
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.address ? formatCompanyAddress(company.address) : "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.vat_number ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.registration_number ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.website ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.email ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {formatPhone(company.phone)}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.industry ?? "-"}
                                </td>
                                {onDeleteCompany ? (
                                    <td className="sticky right-0 z-10 border-l border-slate-200 bg-white px-6 py-4 text-sm shadow-[-8px_0_12px_-12px_rgba(15,23,42,0.45)]">
                                        <div className="flex flex-wrap gap-2">
                                            <Link
                                                href={`/companies/${company.id}/edit`}
                                                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100"
                                            >
                                                Edit
                                            </Link>
                                            <button
                                                type="button"
                                                onClick={() => onDeleteCompany(company)}
                                                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-700"
                                            >
                                                Delete company
                                            </button>
                                        </div>
                                    </td>
                                ) : null}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
