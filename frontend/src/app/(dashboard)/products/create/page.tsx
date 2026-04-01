"use client";

import { useRouter } from "next/navigation";

import ProductCreateForm from "@/components/products/ProductCreateForm";

export default function CreateProductPage() {
    const router = useRouter();

    function handleCreated(): void {
        router.push("/products");
        router.refresh();
    }

    return (
        <main className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-3xl font-bold text-slate-900">Add Product</h1>
                <p className="mt-2 text-sm text-slate-600">
                    Create a new product record for your catalog.
                </p>
            </section>

            <ProductCreateForm onCreated={handleCreated} />
        </main>
    );
}
