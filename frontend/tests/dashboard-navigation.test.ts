import { describe, expect, it } from "vitest";

import { sidebarMenu } from "@/components/navigation/sidebar-menu";

describe("dashboard sidebar navigation", () => {
    it("exposes real KPI and activity links instead of coming-soon placeholders", () => {
        const dashboardSection = sidebarMenu.find((section) => section.title === "Dashboard");
        const activityItem = dashboardSection?.items.find((item) => item.title === "Activity Feed");
        const kpiItem = dashboardSection?.items.find((item) => item.title === "KPIs");

        expect(dashboardSection).toBeTruthy();
        expect(activityItem).toMatchObject({
            title: "Activity Feed",
            href: "/dashboard#activity-feed",
        });
        expect(activityItem?.disabled).toBeUndefined();
        expect(kpiItem).toMatchObject({
            title: "KPIs",
            href: "/dashboard#kpis",
        });
        expect(kpiItem?.disabled).toBeUndefined();
    });
});
