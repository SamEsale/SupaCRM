"use client";

import { useState } from "react";

import ProductsList from "@/components/products/ProductsList";

export default function ProductsPage() {
  const [searchTerm, setSearchTerm] = useState<string>("");

  return (
    <main className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-slate-900">All Products</h1>
        <p className="mt-2 text-sm text-slate-600">
          Search and review all products stored in your catalog.
        </p>

        <div className="mt-6">
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search products by name, SKU, description, price, currency, or status"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
          />
        </div>
      </section>

      <ProductsList searchTerm={searchTerm} />
    </main>
  );
}
