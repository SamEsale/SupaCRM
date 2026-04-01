"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import EditProductModal from "@/components/products/EditProductModal";
import { deleteProduct, getProducts, updateProduct } from "@/services/products.service";
import type { Product } from "@/types/product";

type ProductsListProps = {
  refreshKey?: number;
  searchTerm?: string;
};

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

function matchesProduct(product: Product, searchTerm: string): boolean {
  const normalizedSearch = searchTerm.trim().toLowerCase();

  if (!normalizedSearch) {
    return true;
  }

  const haystack = [
    product.name,
    product.sku,
    product.description,
    product.unit_price,
    product.currency,
    product.is_active ? "active" : "inactive",
    ...product.images.map((image) => image.file_key),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalizedSearch);
}

export default function ProductsList({
  refreshKey = 0,
  searchTerm = "",
}: ProductsListProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string>("");
  const [showInactive, setShowInactive] = useState<boolean>(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isEditOpen, setIsEditOpen] = useState<boolean>(false);

  const loadProducts = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const response = await getProducts();
      setProducts(response.items ?? []);
      setTotal(response.total ?? 0);
    } catch (error) {
      console.error("Failed to load products:", error);
      setError("Failed to load products.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts, refreshKey]);

  const visibleProducts = useMemo(() => {
    const activeFiltered = showInactive
      ? products
      : products.filter((product) => product.is_active);

    return activeFiltered.filter((product) => matchesProduct(product, searchTerm));
  }, [products, showInactive, searchTerm]);

  function openEditModal(product: Product): void {
    setSelectedProduct(product);
    setIsEditOpen(true);
    setActionMessage("");
  }

  function closeEditModal(): void {
    setIsEditOpen(false);
    setSelectedProduct(null);
  }

  async function handleSaved(): Promise<void> {
    setActionMessage("Product updated successfully.");
    await loadProducts();
  }

  async function handleDelete(productId: string): Promise<void> {
    const confirmed = window.confirm("Are you sure you want to delete this product?");
    if (!confirmed) {
      return;
    }

    try {
      setActionMessage("");
      await deleteProduct(productId);
      setActionMessage("Product deleted successfully.");
      await loadProducts();
    } catch (error: unknown) {
      console.error("Failed to delete product:", error);

      let message = "Failed to delete product.";

      if (
        typeof error === "object" &&
        error !== null &&
        "response" in error
      ) {
        const response = (error as {
          response?: { data?: { detail?: string } };
        }).response;

        if (response?.data?.detail) {
          message = response.data.detail;
        }
      }

      setActionMessage(message);
    }
  }

  async function handleToggleActive(product: Product): Promise<void> {
    try {
      setActionMessage("");

      await updateProduct(product.id, {
        is_active: !product.is_active,
      });

      setActionMessage(
        product.is_active
          ? "Product deactivated successfully."
          : "Product reactivated successfully.",
      );

      await loadProducts();
    } catch (error: unknown) {
      console.error("Failed to update product status:", error);

      let message = "Failed to update product status.";

      if (
        typeof error === "object" &&
        error !== null &&
        "response" in error
      ) {
        const response = (error as {
          response?: { data?: { detail?: string } };
        }).response;

        if (response?.data?.detail) {
          message = response.data.detail;
        }
      }

      setActionMessage(message);
    }
  }

  if (loading) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Loading products</h2>
        <p className="mt-2 text-sm text-slate-600">
          Fetching products from the backend API.
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-white p-8 shadow-sm">
        <h2 className="text-xl font-semibold text-red-700">Failed to load products</h2>
        <p className="mt-2 text-sm text-slate-600">{error}</p>
      </section>
    );
  }

  return (
    <>
      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Products</h2>
            <p className="mt-2 text-sm text-slate-600">
              {total} product{total === 1 ? "" : "s"} loaded from the backend API.
            </p>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
            Show inactive products
          </label>
        </div>

        {actionMessage ? (
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            {actionMessage}
          </div>
        ) : null}

        {visibleProducts.length === 0 ? (
          <div className="mt-6 text-sm text-slate-600">
            {searchTerm.trim().length > 0
              ? "No products matched your current search."
              : showInactive
                ? "Your tenant does not have any products yet."
                : "No active products found. Enable the filter to show inactive products."}
          </div>
        ) : (
          <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full border-collapse">
              <thead className="bg-slate-50">
                <tr>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Name
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    SKU
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Description
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Price
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Active
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Images
                  </th>
                  <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleProducts.map((product) => (
                  <tr key={product.id} className="hover:bg-slate-50">
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-900">
                      {product.name}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      {product.sku}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      {product.description ?? ""}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      {formatMoney(product.unit_price, product.currency)}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      {product.is_active ? "Yes" : "No"}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      {product.images.length}
                    </td>
                    <td className="border-b border-slate-200 px-4 py-3 text-sm text-slate-700">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openEditModal(product)}
                          className="rounded-md border border-slate-200 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          onClick={() => void handleToggleActive(product)}
                          className="rounded-md border border-amber-200 px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50"
                        >
                          {product.is_active ? "Deactivate" : "Reactivate"}
                        </button>

                        <button
                          type="button"
                          onClick={() => void handleDelete(product.id)}
                          className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <EditProductModal
        product={selectedProduct}
        isOpen={isEditOpen}
        onClose={closeEditModal}
        onSaved={handleSaved}
      />
    </>
  );
}
