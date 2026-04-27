"use client";

import { useEffect, useState } from "react";

import ProductImageEditor from "@/components/products/ProductImageEditor";
import { sortProductImagesByPosition } from "@/components/products/product-image-utils";
import {
    parseStrictDecimalAmountInput,
    sanitizeStrictDecimalInput,
    shouldBlockStrictDecimalKey,
    TOTAL_AMOUNT_INVALID_MESSAGE,
} from "@/components/finance/amount-utils";
import { createProduct } from "@/services/products.service";
import type { ProductCreateRequest } from "@/types/product";
import { validateProductImageCollection } from "@/components/products/product-image-rules";

type ProductFormMode = "create" | "edit";

type ProductCreateFormProps = {
    onCreated?: () => Promise<void> | void;
    onSuccess?: () => Promise<void> | void;
    onSubmit?: (payload: ProductCreateRequest) => Promise<void>;
    initialValues?: Partial<ProductCreateRequest>;
    mode?: ProductFormMode;
    title?: string;
    description?: string;
    submitLabel?: string;
    submittingLabel?: string;
};

const DEFAULT_FORM_STATE: ProductCreateRequest = {
    name: "",
    sku: "",
    description: "",
    unit_price: "",
    currency: "USD",
    is_active: true,
    images: [],
};

function createBlankImages(count: number): ProductCreateRequest["images"] {
    return Array.from({ length: count }, (_, index) => ({
        position: index + 1,
        file_key: "",
        file_url: null,
    }));
}

function buildInitialState(
    initialValues?: Partial<ProductCreateRequest>,
): ProductCreateRequest {
    const initialImages = initialValues?.images
        ? sortProductImagesByPosition(initialValues.images)
        : createBlankImages(3);

    return {
        ...DEFAULT_FORM_STATE,
        ...initialValues,
        images: initialImages,
    };
}

function parseErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The product could not be saved.";
}

export default function ProductCreateForm({
    onCreated,
    onSuccess,
    onSubmit,
    initialValues,
    mode = "create",
    title,
    description,
    submitLabel,
    submittingLabel,
}: ProductCreateFormProps) {
    const [formData, setFormData] = useState<ProductCreateRequest>(() =>
        buildInitialState(initialValues),
    );
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");

    const resolvedSubmit = onSubmit ?? createProduct;
    const resolvedOnSuccess = onSuccess ?? onCreated ?? (() => undefined);
    const resolvedTitle = title ?? (mode === "edit" ? "Edit product" : "Create product");
    const resolvedDescription =
        description ??
        (mode === "edit"
            ? "Update product details and save changes."
            : "Add a product to the tenant catalog.");
    const resolvedSubmitLabel = submitLabel ?? (mode === "edit" ? "Save changes" : "Create product");
    const resolvedSubmittingLabel = submittingLabel ?? (mode === "edit" ? "Saving..." : "Creating...");
    const resolvedSuccessMessage =
        mode === "edit" ? "Product updated successfully." : "Product created successfully.";

    useEffect(() => {
        setFormData(buildInitialState(initialValues));
        setErrorMessage("");
        setSuccessMessage("");
    }, [initialValues]);

    function updateField<K extends keyof ProductCreateRequest>(
        field: K,
        value: ProductCreateRequest[K],
    ): void {
        setFormData((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
        event.preventDefault();

        try {
            setIsSubmitting(true);
            setErrorMessage("");
            setSuccessMessage("");

            const unitPriceResult = parseStrictDecimalAmountInput(formData.unit_price);
            if (unitPriceResult.error || unitPriceResult.value === null) {
                setErrorMessage(unitPriceResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE);
                return;
            }

            const payload: ProductCreateRequest = {
                ...formData,
                name: formData.name.trim(),
                sku: formData.sku.trim(),
                description: formData.description?.trim() ? formData.description.trim() : null,
                unit_price: String(unitPriceResult.value),
                currency: formData.currency.trim().toUpperCase(),
                images: (formData.images ?? []).map((image, index) => ({
                    position: index + 1,
                    file_key: image.file_key.trim(),
                    file_url: image.file_url ?? null,
                })),
            };

            const imageValidationError = validateProductImageCollection(payload.images);
            if (imageValidationError) {
                setErrorMessage(imageValidationError);
                return;
            }

            await resolvedSubmit(payload);

            setSuccessMessage(resolvedSuccessMessage);
            if (mode === "create") {
                setFormData(buildInitialState());
            }
            await Promise.resolve(resolvedOnSuccess());
        } catch (error) {
            console.error("Failed to save product:", error);
            setErrorMessage(parseErrorMessage(error));
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">{resolvedTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">
                {resolvedDescription}
            </p>
            <p className="mt-3 text-sm text-amber-700">
                Products require between 3 and 15 images. Add, upload, remove, and reorder images below.
            </p>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label
                            className="mb-2 block text-sm font-medium text-slate-700"
                            htmlFor="name"
                        >
                            Name
                        </label>
                        <input
                            id="name"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.name}
                            onChange={(event) => updateField("name", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label
                            className="mb-2 block text-sm font-medium text-slate-700"
                            htmlFor="sku"
                        >
                            SKU
                        </label>
                        <input
                            id="sku"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.sku}
                            onChange={(event) => updateField("sku", event.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label
                            className="mb-2 block text-sm font-medium text-slate-700"
                            htmlFor="unit_price"
                        >
                            Unit price
                        </label>
                        <input
                            id="unit_price"
                            type="text"
                            inputMode="decimal"
                            pattern="[0-9]*[.]?[0-9]*"
                            autoComplete="off"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={formData.unit_price}
                            onChange={(event) =>
                                updateField(
                                    "unit_price",
                                    sanitizeStrictDecimalInput(event.target.value),
                                )
                            }
                            onKeyDown={(event) => {
                                if (shouldBlockStrictDecimalKey(event.key)) {
                                    event.preventDefault();
                                }
                            }}
                            required
                        />
                    </div>

                    <div>
                        <label
                            className="mb-2 block text-sm font-medium text-slate-700"
                            htmlFor="currency"
                        >
                            Currency
                        </label>
                        <input
                            id="currency"
                            maxLength={3}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                            value={formData.currency}
                            onChange={(event) => updateField("currency", event.target.value)}
                            required
                        />
                    </div>
                </div>

                <div>
                    <label
                        className="mb-2 block text-sm font-medium text-slate-700"
                        htmlFor="description"
                    >
                        Description
                    </label>
                    <textarea
                        id="description"
                        className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        value={formData.description ?? ""}
                        onChange={(event) => updateField("description", event.target.value)}
                    />
                </div>

                <div className="flex items-center gap-3">
                    <input
                        id="is_active"
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(event) => updateField("is_active", event.target.checked)}
                    />
                    <label className="text-sm text-slate-700" htmlFor="is_active">
                        Active product
                    </label>
                </div>

                <ProductImageEditor
                    images={formData.images}
                    onChange={(nextImages) =>
                        setFormData((current) => ({
                            ...current,
                            images: nextImages,
                        }))
                    }
                />

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                {successMessage ? (
                    <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                        {successMessage}
                    </div>
                ) : null}

                <div>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
                    </button>
                </div>
            </form>
        </section>
    );
}
