"use client";

import { useState } from "react";

import { createProduct } from "@/services/products.service";
import type { ProductCreateRequest } from "@/types/product";

type ProductCreateFormProps = {
  onCreated: () => Promise<void> | void;
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

export default function ProductCreateForm({
  onCreated,
}: ProductCreateFormProps) {
  const [formData, setFormData] = useState<ProductCreateRequest>(DEFAULT_FORM_STATE);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

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

      const payload: ProductCreateRequest = {
        ...formData,
        description: formData.description?.trim() ? formData.description.trim() : null,
        unit_price: formData.unit_price.trim(),
        currency: formData.currency.trim().toUpperCase(),
        images: [],
      };

      await createProduct(payload);

      setSuccessMessage("Product created successfully.");
      setFormData(DEFAULT_FORM_STATE);
      await onCreated();
    } catch (error) {
      console.error("Failed to create product:", error);
      setErrorMessage("The product could not be created.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-2xl font-semibold text-slate-900">Create product</h2>
      <p className="mt-2 text-sm text-slate-600">
        Add a product to the tenant catalog.
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
              type="number"
              min="0"
              step="0.01"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={formData.unit_price}
              onChange={(event) => updateField("unit_price", event.target.value)}
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
            {isSubmitting ? "Creating..." : "Create product"}
          </button>
        </div>
      </form>
    </section>
  );
}
