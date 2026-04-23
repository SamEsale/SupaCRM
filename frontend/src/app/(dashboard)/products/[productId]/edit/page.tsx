"use client";

import axios from "axios";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import ProductCreateForm from "@/components/products/ProductCreateForm";
import { sortProductImagesByPosition } from "@/components/products/product-image-utils";
import { useAuth } from "@/hooks/use-auth";
import { getProductById, updateProduct } from "@/services/products.service";
import type {
    Product,
    ProductCreateRequest,
    ProductUpdateRequest,
} from "@/types/product";

function getLoadErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
            return "Product not found.";
        }

        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
            return detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "The product edit form could not be loaded from the backend.";
}

export default function EditProductPage() {
    const auth = useAuth();
    const router = useRouter();
    const params = useParams<{ productId: string }>();
    const rawProductId = params?.productId;
    const productId = Array.isArray(rawProductId) ? rawProductId[0] : rawProductId;

    const [product, setProduct] = useState<Product | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        if (!productId) {
            setErrorMessage("Invalid product id.");
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadProduct(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");

                const productResponse = await getProductById(productId);

                if (!isMounted) {
                    return;
                }

                setProduct(productResponse);
            } catch (error) {
                console.error("Failed to load product edit page:", error);
                if (!isMounted) {
                    return;
                }

                setProduct(null);
                setErrorMessage(getLoadErrorMessage(error));
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadProduct();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, productId]);

    const initialValues = useMemo<Partial<ProductCreateRequest> | undefined>(() => {
        if (!product) {
            return undefined;
        }

        return {
            name: product.name,
            sku: product.sku,
            description: product.description,
            unit_price: product.unit_price,
            currency: product.currency,
            is_active: product.is_active,
            images: sortProductImagesByPosition(
                product.images.map((image) => ({
                    position: image.position,
                    file_key: image.file_key,
                    file_url: image.file_url ?? null,
                })),
            ),
        };
    }, [product]);

    async function handleSave(payload: ProductCreateRequest): Promise<void> {
        if (!productId) {
            throw new Error("Invalid product id.");
        }

        const updatePayload: ProductUpdateRequest = {
            name: payload.name,
            sku: payload.sku,
            description: payload.description,
            unit_price: payload.unit_price,
            currency: payload.currency,
            is_active: payload.is_active,
            images: payload.images.map((image) => ({
                position: image.position,
                file_key: image.file_key,
                file_url: image.file_url ?? null,
            })),
        };

        await updateProduct(productId, updatePayload);
    }

    function handleSaved(): void {
        if (!productId) {
            return;
        }

        router.push(`/products/${productId}`);
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Edit Product</h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Update product details and save changes.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {productId ? (
                            <Link
                                href={`/products/${productId}`}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                            >
                                Back to product detail
                            </Link>
                        ) : null}
                        <Link
                            href="/products"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                        >
                            Back to all products
                        </Link>
                    </div>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading product edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching current product data from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load product edit form</h2>
                    <p className="mt-2 text-sm text-slate-600">{errorMessage}</p>
                </section>
            ) : !product ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Product unavailable</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        The requested product could not be found.
                    </p>
                </section>
            ) : (
                <ProductCreateForm
                    mode="edit"
                    initialValues={initialValues}
                    onSubmit={handleSave}
                    onSuccess={handleSaved}
                    title="Edit product"
                    description="Modify product fields and save changes."
                    submitLabel="Save changes"
                    submittingLabel="Saving..."
                />
            )}
        </main>
    );
}
