import type { Contact } from "@/types/crm";

interface ContactsListProps {
    contacts: Contact[];
    total: number;
}

function formatContactName(contact: Contact): string {
    return [contact.first_name, contact.last_name].filter(Boolean).join(" ");
}

export default function ContactsList({
    contacts,
    total,
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
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200 bg-white">
                        {contacts.map((contact) => (
                            <tr key={contact.id}>
                                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                                    {formatContactName(contact) || "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.email ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.phone ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.company ?? "-"}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-700">
                                    {contact.job_title ?? "-"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
