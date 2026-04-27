import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/constants/env";

const mocks = vi.hoisted(() => ({
    uploadFileToStorage: vi.fn(),
}));

vi.mock("@/services/uploads.service", () => ({
    uploadFileToStorage: mocks.uploadFileToStorage,
}));

import ProductCreateForm from "@/components/products/ProductCreateForm";

function fillRequiredFields(): void {
    fireEvent.change(screen.getByLabelText(/^Name$/i), {
        target: { value: "Catalog Product" },
    });
    fireEvent.change(screen.getByLabelText(/^SKU$/i), {
        target: { value: "catalog-product" },
    });
    fireEvent.change(screen.getByLabelText(/^Unit price$/i), {
        target: { value: "19.99" },
    });
    fireEvent.change(screen.getByLabelText(/^Currency$/i), {
        target: { value: "USD" },
    });
}

beforeEach(() => {
    mocks.uploadFileToStorage.mockReset();
    mocks.uploadFileToStorage.mockImplementation(async (file: File) => ({
        bucket: "supacrm",
        file_key: `product-images/tenant-1/${file.name}`,
        file_url: null,
    }));
});

async function uploadSelectedImage(label: RegExp, fileName: string, callCount: number): Promise<void> {
    const selectedFile = new File(["image-bytes"], fileName, {
        type: "image/png",
    });

    fireEvent.change(screen.getByLabelText(label), {
        target: { files: [selectedFile] },
    });

    await waitFor(() => {
        expect(mocks.uploadFileToStorage).toHaveBeenCalledTimes(callCount);
    });
}

afterEach(() => {
    cleanup();
});

describe("product image upload workflow", () => {
    it("uploads selected images into the product form and preserves the upload result", async () => {
        const onSubmit = vi.fn();

        render(<ProductCreateForm onSubmit={onSubmit} />);

        fillRequiredFields();

        await uploadSelectedImage(/upload image 1/i, "product-1.png", 1);
        await uploadSelectedImage(/upload image 2/i, "product-2.png", 2);
        await uploadSelectedImage(/upload image 3/i, "product-3.png", 3);

        await waitFor(() => {
            expect(screen.getAllByAltText(/product image \d+/i)).toHaveLength(3);
        });

        expect((screen.getByAltText(/product image 1/i) as HTMLImageElement).src).toBe(
            new URL(
                "/media/product-images/tenant-1/product-1.png",
                API_BASE_URL,
            ).toString(),
        );
        expect((screen.getByAltText(/product image 2/i) as HTMLImageElement).src).toBe(
            new URL(
                "/media/product-images/tenant-1/product-2.png",
                API_BASE_URL,
            ).toString(),
        );
        expect((screen.getByAltText(/product image 3/i) as HTMLImageElement).src).toBe(
            new URL(
                "/media/product-images/tenant-1/product-3.png",
                API_BASE_URL,
            ).toString(),
        );

        fireEvent.click(screen.getByRole("button", { name: /create product/i }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });

        expect(onSubmit).toHaveBeenCalledWith(
            {
                name: "Catalog Product",
                sku: "catalog-product",
                description: null,
                unit_price: "19.99",
                currency: "USD",
                is_active: true,
                images: [
                    {
                        position: 1,
                        file_key: "product-images/tenant-1/product-1.png",
                        file_url: new URL(
                            "/media/product-images/tenant-1/product-1.png",
                            API_BASE_URL,
                        ).toString(),
                    },
                    {
                        position: 2,
                        file_key: "product-images/tenant-1/product-2.png",
                        file_url: new URL(
                            "/media/product-images/tenant-1/product-2.png",
                            API_BASE_URL,
                        ).toString(),
                    },
                    {
                        position: 3,
                        file_key: "product-images/tenant-1/product-3.png",
                        file_url: new URL(
                            "/media/product-images/tenant-1/product-3.png",
                            API_BASE_URL,
                        ).toString(),
                    },
                ],
            },
        );
    });

    it("keeps product unit price strict and strips exponent characters before submit", async () => {
        render(<ProductCreateForm onSubmit={vi.fn()} />);

        fillRequiredFields();

        const unitPriceInput = screen.getByLabelText(/^Unit price$/i) as HTMLInputElement;
        fireEvent.change(unitPriceInput, {
            target: { value: "12e3" },
        });
        expect(unitPriceInput.value).toBe("123");

        fireEvent.change(unitPriceInput, {
            target: { value: "10E3" },
        });
        expect(unitPriceInput.value).toBe("103");

        fireEvent.change(unitPriceInput, {
            target: { value: "99+-" },
        });
        expect(unitPriceInput.value).toBe("99");

        fireEvent.change(unitPriceInput, {
            target: { value: "€5000" },
        });
        expect(unitPriceInput.value).toBe("5000");
    });
});
