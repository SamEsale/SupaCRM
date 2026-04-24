export type SidebarSubmenuItem = {
    title: string;
    href?: string;
    disabled?: boolean;
};

export type SidebarMenuSection = {
    title: string;
    items: SidebarSubmenuItem[];
};

export const sidebarMenu: SidebarMenuSection[] = [
    {
        title: "Dashboard",
        items: [
            { title: "Overview", href: "/dashboard" },
            { title: "Activity Feed", disabled: true },
            { title: "KPIs", disabled: true },
        ],
    },
    {
        title: "Contacts",
        items: [
            { title: "All Contacts", href: "/contacts" },
            { title: "All Companies", href: "/companies" },
            { title: "Add Contact", href: "/contacts/create" },
            { title: "Add Company", href: "/companies/create" },
            { title: "Add Lead", href: "/sales/leads/create" },
        ],
    },
    {
        title: "Sales",
        items: [
            { title: "All Deals", href: "/deals" },
            { title: "Add Deal", href: "/deals/create" },
            { title: "Add Lead", href: "/sales/leads/create" },
            { title: "Sales Pipeline", href: "/sales/pipeline" },
            { title: "Opportunities", href: "/sales/opportunities" },
        ],
    },
    {
        title: "Marketing",
        items: [
            { title: "All Products", href: "/products" },
            { title: "Add Product", href: "/products/create" },
            { title: "Campaigns", disabled: true },
            { title: "Email Campaigns", disabled: true },
            { title: "Lead Capture", disabled: true },
            { title: "Segments", disabled: true },
        ],
    },
    {
        title: "Finance",
        items: [
            { title: "Overview", href: "/finance" },
            { title: "All Invoices", href: "/finance/invoices" },
            { title: "Create Invoice", href: "/finance/invoices/create" },
            { title: "All Quotes", href: "/finance/quotes" },
            { title: "Create Quote", href: "/finance/quotes/create" },
            { title: "Expenses", disabled: true },
            { title: "Accounting Settings", disabled: true },
        ],
    },
    {
        title: "Payments",
        items: [
            { title: "Gateway Settings", disabled: true },
            { title: "Integrations", disabled: true },
            { title: "Transactions", disabled: true },
            { title: "Subscription Billing", href: "/finance/payments/subscription-billing" },
        ],
    },
    {
        title: "Settings",
        items: [
            { title: "Overview", href: "/settings" },
            { title: "Company Settings", href: "/settings/company" },
            { title: "Branding", href: "/settings/branding" },
        ],
    },
    {
        title: "Reports",
        items: [
            { title: "Sales Reports", disabled: true },
            { title: "Contact Reports", disabled: true },
            { title: "Company Reports", disabled: true },
            { title: "Finance Reports", disabled: true },
            { title: "Support Reports", disabled: true },
        ],
    },
    {
        title: "Support",
        items: [
            { title: "All Tickets", disabled: true },
            { title: "Open Inbox", disabled: true },
            { title: "Email Replies", disabled: true },
            { title: "Knowledge Base", disabled: true },
            { title: "Customer Contacts", href: "/contacts" },
        ],
    },
];
