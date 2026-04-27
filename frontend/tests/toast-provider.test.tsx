import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ToastProvider, useToast } from "@/components/feedback/ToastProvider";

function ToastHarness() {
    const toast = useToast();

    return (
        <button
            type="button"
            onClick={() => toast.success("Saved successfully.")}
        >
            Trigger toast
        </button>
    );
}

describe("ToastProvider", () => {
    it("renders a reusable success notification", async () => {
        render(
            <ToastProvider>
                <ToastHarness />
            </ToastProvider>,
        );

        fireEvent.click(screen.getByRole("button", { name: /trigger toast/i }));

        await waitFor(() => {
            expect(screen.getByText("Saved successfully.")).toBeTruthy();
        });
    });
});
