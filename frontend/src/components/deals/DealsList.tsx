"use client";

import type { Company, Contact, Deal } from "@/types/crm";
import type { Product } from "@/types/product";

type DealsListProps = {
    deals: Deal[];
    total: number;
    companies: Company[];
    contacts: Contact[];
    products: Product[];
};

function formatLabel(value: string): string {
    return value
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatMoney(amount: string, currency: string): string {
    const value = Number(amount);

    if (Number.isNaN(value)) {
        return `${amount} ${currency}`;
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(value);
}

function getCompanyName(companies: Company[], companyId: string): string {
    return companies.find((company) => company.id === companyId)?.name ?? companyId;
}

function getContactName(contacts: Contact[], contactId: string | null): string {
    if (!contactId) {
        return "";
    }

    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) {
        return contactId;
    }

    return `${contact.first_name} ${contact.last_name ?? ""}`.trim();
}

function getProductName(products: Product[], productId: string | null): string {
    if (!productId) {
        return "";
    }

    const product = products.find((item) => item.id === productId);
    if (!product) {
        return productId;
    }

    return product.name;
}

export default function DealsList({
    deals,
    total,
    companies,
    contacts,
    products,
}: DealsListProps) {
    if (deals.length === 0) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Deals</h2>
                <p className="mt-2 text-sm text-slate-600">
                    Your tenant does not have any deals yet.
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Deals</h2>
            <p className="mt-2 text-sm text-slate-600">
                {total} deal{total === 1 ? "" : "s"} loaded from the backend API.
            </p>

            <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full border-collapse">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Name
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Company
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Contact
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Product
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Amount
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Stage
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Status
                            </th>
                            <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Expected Close
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {deals.map((deal) => (
                            <tr key={deal.id} className="hover:bg-slate-50">
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-900">
                                    {deal.name}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {getCompanyName(companies, deal.company_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {getContactName(contacts, deal.contact_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {getProductName(products, deal.product_id)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatMoney(deal.amount, deal.currency)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatLabel(deal.stage)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {formatLabel(deal.status)}
                                </td>
                                <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                                    {deal.expected_close_date ?? ""}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
