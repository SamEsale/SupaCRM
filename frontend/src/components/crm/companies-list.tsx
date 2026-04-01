import type { Company } from "@/types/crm";

interface CompaniesListProps {
    companies: Company[];
    total: number;
}

function formatPhone(phone: string | null): string {
    if (!phone) {
        return "—";
    }

    return phone.replace(/-/g, "");
}

export default function CompaniesList({
    companies,
    total,
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
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200 bg-white">
                        {companies.map((company) => (
                            <tr key={company.id}>
                                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                                    {company.name}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.address ?? "—"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.vat_number ?? "—"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.registration_number ?? "—"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.website ?? "—"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.email ?? "—"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {formatPhone(company.phone)}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {company.industry ?? "—"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}