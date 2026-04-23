import Link from "next/link";

import type { Contact } from "@/types/crm";

interface ContactsListProps {
    contacts: Contact[];
    total: number;
    onDeleteContact?: (contact: Contact) => void;
}

function formatContactName(contact: Contact): string {
    return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
}

export default function ContactsList({
    contacts,
    total,
    onDeleteContact,
}: ContactsListProps) {
    return (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
                <h2 className="text-lg font-semibold text-slate-900">Contacts</h2>
                <p className="mt-1 text-sm text-slate-600">
                    {total} contact{total === 1 ? "" : "s"} loaded from the backend API.
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
                                Email
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Phone
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Company
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Job Title
                            </th>
                            {onDeleteContact ? (
                                <th className="sticky right-0 z-10 bg-slate-50 px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                                    Actions
                                </th>
                            ) : null}
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200 bg-white">
                        {contacts.map((contact) => (
                            <tr key={contact.id}>
                                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                                    <Link
                                        href={`/contacts/${contact.id}`}
                                        className="underline-offset-2 hover:underline"
                                    >
                                        {formatContactName(contact) || "-"}
                                    </Link>
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.email ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.phone ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.company_id ? (
                                        <Link
                                            href={`/companies/${contact.company_id}`}
                                            className="underline-offset-2 hover:underline"
                                        >
                                            {contact.company ?? contact.company_id}
                                        </Link>
                                    ) : (
                                        contact.company ?? "-"
                                    )}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.job_title ?? "-"}
                                </td>
                                {onDeleteContact ? (
                                    <td className="sticky right-0 z-10 border-l border-slate-200 bg-white px-6 py-4 text-sm shadow-[-8px_0_12px_-12px_rgba(15,23,42,0.45)]">
                                        <div className="flex flex-wrap gap-2">
                                            <Link
                                                href={`/contacts/${contact.id}/edit`}
                                                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100"
                                            >
                                                Edit
                                            </Link>
                                            <button
                                                type="button"
                                                onClick={() => onDeleteContact(contact)}
                                                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-700"
                                            >
                                                Delete contact
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
