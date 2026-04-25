import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/constants/env";

const mocks = vi.hoisted(() => ({
    getProductById: vi.fn(),
    getDeals: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({
    useAuth: () => ({
        isReady: true,
        isAuthenticated: true,
        accessToken: "token",
    }),
}));

vi.mock("next/navigation", () => ({
    useParams: () => ({
        productId: "product-1",
    }),
}));

vi.mock("@/services/products.service", () => ({
    getProductById: mocks.getProductById,
}));

vi.mock("@/services/deals.service", () => ({
    getDeals: mocks.getDeals,
}));

import ProductDetailPage from "@/app/(dashboard)/products/[productId]/page";

beforeEach(() => {
    mocks.getProductById.mockReset();
    mocks.getDeals.mockReset();

    mocks.getProductById.mockResolvedValue({
        id: "product-1",
        tenant_id: "tenant-1",
        name: "Catalog Product",
        sku: "CAT-001",
        description: "A test product",
        unit_price: "19.99",
        currency: "USD",
        is_active: true,
        created_at: "2026-04-08T00:00:00.000Z",
        updated_at: "2026-04-08T00:00:00.000Z",
        images: [
            {
                id: "image-1",
                tenant_id: "tenant-1",
                product_id: "product-1",
                position: 3,
                file_key: "product-images/tenant-1/catalog-product-3.png",
                created_at: "2026-04-08T00:00:00.000Z",
                file_url: null,
            },
            {
                id: "image-2",
                tenant_id: "tenant-1",
                product_id: "product-1",
                position: 1,
                file_key: "product-images/tenant-1/catalog-product-1.png",
                created_at: "2026-04-08T00:00:00.000Z",
                file_url: null,
            },
            {
                id: "image-3",
                tenant_id: "tenant-1",
                product_id: "product-1",
                position: 2,
                file_key: "product-images/tenant-1/catalog-product-2.png",
                created_at: "2026-04-08T00:00:00.000Z",
                file_url: null,
            },
        ],
    });
    mocks.getDeals.mockResolvedValue({
        items: [],
        total: 0,
    });
});

afterEach(() => {
    cleanup();
});

describe("product detail media rendering", () => {
    it("renders a gallery and switches the main image when a thumbnail is clicked", async () => {
        render(<ProductDetailPage />);

        await waitFor(() => {
            expect(mocks.getProductById).toHaveBeenCalledWith("product-1");
        });

        const mainImage = await screen.findByAltText(/catalog product product image 1/i);
        expect((mainImage as HTMLImageElement).src).toBe(
            new URL(
                "/media/product-images/tenant-1/catalog-product-1.png",
                API_BASE_URL,
            ).toString(),
        );

        expect(screen.queryByText(/catalog-product-1\.png/i)).toBeNull();

        fireEvent.click(screen.getByRole("button", { name: /show product image 2/i }));

        const selectedImage = await screen.findByAltText(/catalog product product image 2/i);
        expect((selectedImage as HTMLImageElement).src).toBe(
            new URL(
                "/media/product-images/tenant-1/catalog-product-2.png",
                API_BASE_URL,
            ).toString(),
        );
    });
});
