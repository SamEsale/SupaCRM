"use client";

import { useEffect, useState } from "react";

import {
  parseStrictDecimalAmountInput,
  sanitizeStrictDecimalInput,
  shouldBlockStrictDecimalKey,
  TOTAL_AMOUNT_INVALID_MESSAGE,
} from "@/components/finance/amount-utils";
import { updateProduct } from "@/services/products.service";
import type { Product, ProductUpdateRequest } from "@/types/product";

type EditProductModalProps = {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => Promise<void> | void;
};

type FormState = {
  name: string;
  sku: string;
  description: string;
  unit_price: string;
  currency: string;
  is_active: boolean;
};

function buildInitialState(product: Product | null): FormState {
  return {
    name: product?.name ?? "",
    sku: product?.sku ?? "",
    description: product?.description ?? "",
    unit_price: product?.unit_price ?? "",
    currency: product?.currency ?? "USD",
    is_active: product?.is_active ?? true,
  };
}

export default function EditProductModal({
  product,
  isOpen,
  onClose,
  onSaved,
}: EditProductModalProps) {
  const [formData, setFormData] = useState<FormState>(buildInitialState(product));
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [unitPriceError, setUnitPriceError] = useState<string>("");

  useEffect(() => {
    setFormData(buildInitialState(product));
    setErrorMessage("");
    setUnitPriceError("");
  }, [product, isOpen]);

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]): void {
    setFormData((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (!product) {
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage("");
      setUnitPriceError("");

      const unitPriceResult = parseStrictDecimalAmountInput(formData.unit_price);
      if (unitPriceResult.error || unitPriceResult.value === null) {
        setUnitPriceError(unitPriceResult.error ?? TOTAL_AMOUNT_INVALID_MESSAGE);
        return;
      }

      const payload: ProductUpdateRequest = {
        name: formData.name.trim(),
        sku: formData.sku.trim(),
        description: formData.description.trim() ? formData.description.trim() : null,
        unit_price: String(unitPriceResult.value),
        currency: formData.currency.trim().toUpperCase(),
        is_active: formData.is_active,
      };

      await updateProduct(product.id, payload);
      await onSaved();
      onClose();
    } catch (error: unknown) {
      console.error("Failed to update product:", error);

      let message = "Failed to update product.";

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

      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isOpen || !product) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Edit product</h2>
            <p className="mt-2 text-sm text-slate-600">
              Update product details and active status.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
          >
            Close
          </button>
        </div>

        <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-name">
                Name
              </label>
              <input
                id="edit-name"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={formData.name}
                onChange={(event) => updateField("name", event.target.value)}
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-sku">
                SKU
              </label>
              <input
                id="edit-sku"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={formData.sku}
                onChange={(event) => updateField("sku", event.target.value)}
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-unit-price">
                Unit price
              </label>
              <input
                id="edit-unit-price"
                type="text"
                inputMode="decimal"
                pattern="[0-9]*[.]?[0-9]*"
                autoComplete="off"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={formData.unit_price}
                onChange={(event) => {
                  updateField("unit_price", sanitizeStrictDecimalInput(event.target.value));
                  setUnitPriceError("");
                }}
                onKeyDown={(event) => {
                  if (shouldBlockStrictDecimalKey(event.key)) {
                    event.preventDefault();
                  }
                }}
                required
              />
              {unitPriceError ? (
                <p className="mt-1 text-sm text-red-600">{unitPriceError}</p>
              ) : null}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-currency">
                Currency
              </label>
              <input
                id="edit-currency"
                maxLength={3}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                value={formData.currency}
                onChange={(event) => updateField("currency", event.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-description">
              Description
            </label>
            <textarea
              id="edit-description"
              className="min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={formData.description}
              onChange={(event) => updateField("description", event.target.value)}
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              id="edit-is-active"
              type="checkbox"
              checked={formData.is_active}
              onChange={(event) => updateField("is_active", event.target.checked)}
            />
            <label className="text-sm text-slate-700" htmlFor="edit-is-active">
              Active product
            </label>
          </div>

          {errorMessage ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Saving..." : "Save changes"}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
