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
            { title: "Onboarding", href: "/onboarding" },
            { title: "Activity Feed", href: "/dashboard#activity-feed" },
            { title: "KPIs", href: "/dashboard#kpis" },
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
            { title: "Integrations", href: "/marketing/integrations" },
            { title: "Campaigns", href: "/marketing/campaigns" },
            { title: "WhatsApp Intake", href: "/marketing/whatsapp-intake" },
        ],
    },
    {
        title: "Finance",
        items: [
            { title: "Overview", href: "/finance" },
            { title: "Accounting", href: "/finance/accounting" },
            { title: "All Invoices", href: "/finance/invoices" },
            { title: "Create Invoice", href: "/finance/invoices/create" },
            { title: "All Quotes", href: "/finance/quotes" },
            { title: "Create Quote", href: "/finance/quotes/create" },
            { title: "Expenses", href: "/finance/expenses" },
        ],
    },
    {
        title: "Payments",
        items: [
            { title: "Gateway Settings", href: "/finance/payments/gateway-settings" },
            { title: "Integrations", href: "/finance/payments/integrations" },
            { title: "Transactions", href: "/finance/payments" },
            { title: "Subscription Billing", href: "/finance/payments/subscription-billing" },
        ],
    },
    {
        title: "Reports",
        items: [
            { title: "Sales Reports", href: "/reports/sales" },
            { title: "Contact Reports", href: "/reports/contacts" },
            { title: "Company Reports", href: "/reports/companies" },
            { title: "Finance Reports", href: "/reports/finance" },
            { title: "Support Reports", href: "/reports/support" },
        ],
    },
    {
        title: "Support",
        items: [
            { title: "All Tickets", href: "/support" },
            { title: "Create Ticket", href: "/support/create" },
            { title: "Email Replies", disabled: true },
            { title: "Knowledge Base", disabled: true },
            { title: "Customer Contacts", href: "/contacts" },
        ],
    },
    {
        title: "Settings",
        items: [
            { title: "Company", href: "/settings/company" },
            { title: "Branding", href: "/settings/branding" },
            { title: "Integrations", href: "/settings/integrations" },
            { title: "Users & Roles", href: "/settings/users" },
            { title: "Membership", href: "/settings/membership" },
            { title: "Security", href: "/settings/security" },
        ],
    },
];
