import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProductCreateForm from "@/components/products/ProductCreateForm";
import type { ProductCreateRequest } from "@/types/product";

function buildImages(count: number): ProductCreateRequest["images"] {
    return Array.from({ length: count }, (_, index) => {
        const position = index + 1;
        return {
            position,
            file_key: `products/image-${position}.png`,
            file_url: null,
        };
    });
}

function buildPayload(images: ProductCreateRequest["images"]): ProductCreateRequest {
    return {
        name: "Catalog Product",
        sku: "catalog-product",
        description: "Catalog product description",
        unit_price: "19.99",
        currency: "USD",
        is_active: true,
        images,
    };
}

afterEach(() => {
    cleanup();
});

describe("product image rule enforcement", () => {
    it("blocks create submission when fewer than 3 product images are present", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                onSubmit={onSubmit}
                initialValues={buildPayload(buildImages(2))}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: /create product/i }));

        await waitFor(() => {
            expect(
                screen.getByText(/at least 3 product images are required\./i),
            ).toBeTruthy();
        });

        expect(onSubmit).not.toHaveBeenCalled();
    });

    it("blocks create submission when more than 15 product images are present", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                onSubmit={onSubmit}
                initialValues={buildPayload(buildImages(16))}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: /create product/i }));

        await waitFor(() => {
            expect(
                screen.getByText(/no more than 15 product images are allowed\./i),
            ).toBeTruthy();
        });

        expect(onSubmit).not.toHaveBeenCalled();
    });

    it("allows create submission when exactly 3 product images are present", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                onSubmit={onSubmit}
                initialValues={buildPayload(buildImages(3))}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: /create product/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(buildPayload(buildImages(3)));
    });

    it("allows create submission when exactly 15 product images are present", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                onSubmit={onSubmit}
                initialValues={buildPayload(buildImages(15))}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: /create product/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(buildPayload(buildImages(15)));
    });

    it("shows the primary image indicator and add-image control", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                mode="edit"
                onSubmit={onSubmit}
                initialValues={{
                    ...buildPayload(buildImages(3)),
                }}
            />,
        );

        expect(screen.getByText(/image 1 is the primary image/i)).toBeTruthy();
        expect((screen.getByRole("button", { name: /move image 1 left/i }) as HTMLButtonElement).disabled).toBe(true);
        expect((screen.getByRole("button", { name: /move image 3 right/i }) as HTMLButtonElement).disabled).toBe(true);
        expect(screen.getAllByAltText(/product image \d+/i)).toHaveLength(3);

        fireEvent.click(screen.getByRole("button", { name: /add image/i }));

        await waitFor(() => {
            expect(screen.getAllByLabelText(/upload image \d+/i)).toHaveLength(4);
        });
    });

    it("reorders images through the drag handle and preserves the saved order", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                mode="edit"
                onSubmit={onSubmit}
                initialValues={{
                    ...buildPayload(buildImages(3)),
                }}
            />,
        );

        const dataTransfer = {
            effectAllowed: "",
            setData: vi.fn(),
            getData: vi.fn(),
        } as unknown as DataTransfer;

        fireEvent.dragStart(screen.getByRole("button", { name: /drag image 1 to reorder/i }), {
            dataTransfer,
        });

        const targetCard = screen
            .getByRole("button", { name: /move image 3 left/i })
            .closest("article");
        expect(targetCard).toBeTruthy();

        fireEvent.dragOver(targetCard as Element, {
            dataTransfer,
        });
        fireEvent.drop(targetCard as Element, {
            dataTransfer,
        });

        fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(
            {
                name: "Catalog Product",
                sku: "catalog-product",
                description: "Catalog product description",
                unit_price: "19.99",
                currency: "USD",
                is_active: true,
                images: [
                    {
                        position: 1,
                        file_key: "products/image-2.png",
                        file_url: null,
                    },
                    {
                        position: 2,
                        file_key: "products/image-3.png",
                        file_url: null,
                    },
                    {
                        position: 3,
                        file_key: "products/image-1.png",
                        file_url: null,
                    },
                ],
            },
        );
    });

    it("reorders images through move buttons as a fallback control", async () => {
        const onSubmit = vi.fn();

        render(
            <ProductCreateForm
                mode="edit"
                onSubmit={onSubmit}
                initialValues={{
                    ...buildPayload(buildImages(3)),
                }}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: /move image 1 right/i }));
        fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(
            {
                name: "Catalog Product",
                sku: "catalog-product",
                description: "Catalog product description",
                unit_price: "19.99",
                currency: "USD",
                is_active: true,
                images: [
                    {
                        position: 1,
                        file_key: "products/image-2.png",
                        file_url: null,
                    },
                    {
                        position: 2,
                        file_key: "products/image-1.png",
                        file_url: null,
                    },
                    {
                        position: 3,
                        file_key: "products/image-3.png",
                        file_url: null,
                    },
                ],
            },
        );
    });
});
