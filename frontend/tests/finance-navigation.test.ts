import { describe, expect, it } from "vitest";

import { sidebarMenu } from "@/components/navigation/sidebar-menu";

describe("finance navigation", () => {
    it("enables the expenses route in the sidebar", () => {
        const financeSection = sidebarMenu.find((section) => section.title === "Finance");
        const expensesItem = financeSection?.items.find((item) => item.title === "Expenses");

        expect(expensesItem).toBeDefined();
        expect(expensesItem?.href).toBe("/finance/expenses");
        expect(expensesItem?.disabled).toBeUndefined();
    });
});
