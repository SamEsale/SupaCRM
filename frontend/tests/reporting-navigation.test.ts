import { describe, expect, it } from "vitest";

import { sidebarMenu } from "@/components/navigation/sidebar-menu";

describe("reporting sidebar navigation", () => {
    it("exposes real contact, company, and support report routes", () => {
        const reportsSection = sidebarMenu.find((section) => section.title === "Reports");
        const contactReports = reportsSection?.items.find((item) => item.title === "Contact Reports");
        const companyReports = reportsSection?.items.find((item) => item.title === "Company Reports");
        const supportReports = reportsSection?.items.find((item) => item.title === "Support Reports");

        expect(contactReports).toMatchObject({
            title: "Contact Reports",
            href: "/reports/contacts",
        });
        expect(contactReports?.disabled).toBeUndefined();

        expect(companyReports).toMatchObject({
            title: "Company Reports",
            href: "/reports/companies",
        });
        expect(companyReports?.disabled).toBeUndefined();

        expect(supportReports).toMatchObject({
            title: "Support Reports",
            href: "/reports/support",
        });
        expect(supportReports?.disabled).toBeUndefined();
    });
});
