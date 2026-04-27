"use client";

import axios from "axios";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import ProductImageGallery from "@/components/products/ProductImageGallery";
import { sortProductImagesByPosition } from "@/components/products/product-image-utils";
import { useAuth } from "@/hooks/use-auth";
import { getDeals } from "@/services/deals.service";
import { getProductById } from "@/services/products.service";
import type { Deal } from "@/types/crm";
import type { Product } from "@/types/product";

function formatMoney(amount: string, currency: string): string {
    const value = Number(amount);

    if (Number.isNaN(value)) {
        return `${amount} ${currency}`;
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(value);
}

function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("en-US");
}

function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function formatLabel(value: string): string {
    return value
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

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

    return "The product could not be loaded from the backend.";
}

export default function ProductDetailPage() {
    const auth = useAuth();
    const params = useParams<{ productId: string }>();
    const rawProductId = params?.productId;
    const productId = Array.isArray(rawProductId) ? rawProductId[0] : rawProductId;

    const [product, setProduct] = useState<Product | null>(null);
    const [relatedDeals, setRelatedDeals] = useState<Deal[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [relatedWarning, setRelatedWarning] = useState<string>("");

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

        async function loadProductDetail(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                setRelatedWarning("");
                setRelatedDeals([]);

                const productResponse = await getProductById(productId);

                let deals: Deal[] = [];
                try {
                    const dealsResponse = await getDeals({
                        product_id: productId,
                        limit: 10,
                        offset: 0,
                    });
                    deals = dealsResponse.items ?? [];
                } catch (error) {
                    console.warn("Failed to load product-related deals:", error);
                    if (isMounted) {
                        setRelatedWarning("Related deals could not be loaded.");
                    }
                }

                if (!isMounted) {
                    return;
                }

                setProduct(productResponse);
                setRelatedDeals(deals);
            } catch (error) {
                console.error("Failed to load product detail:", error);
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

        void loadProductDetail();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, productId]);

    const detailRows = useMemo(() => {
        if (!product) {
            return [];
        }

        return [
            { label: "Product Name", value: product.name },
            { label: "SKU", value: product.sku || "Not set" },
            { label: "Price", value: formatMoney(product.unit_price, product.currency) },
            { label: "Currency", value: product.currency || "Not set" },
            { label: "Description", value: product.description?.trim() ? product.description : "No description" },
            { label: "Status", value: product.is_active ? "Active" : "Inactive" },
            { label: "Images", value: String(product.images.length) },
            { label: "Created At", value: formatDateTime(product.created_at) },
            { label: "Updated At", value: formatDateTime(product.updated_at) },
        ];
    }, [product]);

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            {product ? product.name : "Product Details"}
                        </h1>
                        <p className="mt-2 text-sm text-slate-600">
                            Read-only product details.
                        </p>
                    </div>

                    <Link
                        href={productId ? `/products/${productId}/edit` : "/products"}
                        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                        Edit Product
                    </Link>

                    <Link
                        href="/products"
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                        Back to all products
                    </Link>
                </div>
            </section>

            {isLoading ? (
                <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Loading product details</h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Fetching product and related deals from the backend API.
                    </p>
                </section>
            ) : errorMessage ? (
                <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
                    <h2 className="text-xl font-semibold text-red-700">Failed to load product</h2>
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
                <>
                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <div className="grid gap-4 md:grid-cols-2">
                            {detailRows.map((row) => (
                                <div key={row.label} className="rounded-lg border border-slate-200 p-4">
                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                        {row.label}
                                    </p>
                                    <p className="mt-1 text-sm text-slate-900">{row.value}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    {product.images.length > 0 ? (
                        <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                            <h2 className="text-xl font-semibold text-slate-900">Product gallery</h2>
                            <p className="mt-2 text-sm text-slate-600">
                                Browse the primary image and switch between thumbnails.
                            </p>

                            <div className="mt-5">
                                <ProductImageGallery
                                    images={sortProductImagesByPosition(product.images)}
                                    productName={product.name}
                                />
                            </div>
                        </section>
                    ) : null}

                    {relatedWarning ? (
                        <section className="rounded-xl border border-amber-200 bg-white p-4 shadow-sm">
                            <p className="text-sm text-amber-700">{relatedWarning}</p>
                        </section>
                    ) : null}

                    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                        <h2 className="text-xl font-semibold text-slate-900">Recent Deals Using This Product</h2>
                        <p className="mt-2 text-sm text-slate-600">
                            Most recent deals linked to this product.
                        </p>

                        {relatedDeals.length === 0 ? (
                            <p className="mt-4 text-sm text-slate-600">No deals found for this product.</p>
                        ) : (
                            <ul className="mt-4 space-y-2">
                                {relatedDeals.map((deal) => (
                                    <li
                                        key={deal.id}
                                        className="rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700"
                                    >
                                        <Link
                                            href={`/deals/${deal.id}`}
                                            className="font-medium text-slate-900 underline underline-offset-2 transition hover:text-slate-700"
                                        >
                                            {deal.name}
                                        </Link>
                                        <span className="ml-2 text-slate-500">
                                            {formatLabel(deal.stage)} - {formatMoney(deal.amount, deal.currency)}
                                        </span>
                                        {deal.expected_close_date ? (
                                            <span className="ml-2 text-slate-500">
                                                (Expected {formatDate(deal.expected_close_date)})
                                            </span>
                                        ) : null}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}
