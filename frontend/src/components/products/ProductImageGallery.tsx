"use client";

import { useMemo, useState } from "react";

import { resolveProductImageUrl, sortProductImagesByPosition } from "@/components/products/product-image-utils";
import type { ProductImage } from "@/types/product";

type ProductImageGalleryProps = {
    images: ProductImage[];
    productName: string;
};

export default function ProductImageGallery({
    images,
    productName,
}: ProductImageGalleryProps) {
    const sortedImages = useMemo(
        () => sortProductImagesByPosition(images),
        [images],
    );
    const [selectedIndex, setSelectedIndex] = useState<number>(0);

    const activeIndex =
        sortedImages.length === 0
            ? 0
            : Math.min(selectedIndex, sortedImages.length - 1);
    const selectedImage = sortedImages[activeIndex] ?? sortedImages[0] ?? null;
    const selectedPreviewUrl = selectedImage ? resolveProductImageUrl(selectedImage) : null;

    if (sortedImages.length === 0) {
        return (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-sm text-slate-600">
                No images are available for this product.
            </div>
        );
    }

    return (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
                <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-slate-900 px-5 py-4">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                            Primary image
                        </p>
                        <p className="mt-1 text-sm text-slate-200">
                            {selectedImage
                                ? `Image ${selectedImage.position} of ${sortedImages.length}`
                                : "No image selected"}
                        </p>
                    </div>

                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                        {sortedImages.length} images
                    </span>
                </div>

                <div className="relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950 p-4">
                    <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-100 shadow-2xl">
                        {selectedPreviewUrl ? (
                            <img
                                src={selectedPreviewUrl}
                                alt={`${productName} product image ${selectedImage.position}`}
                                className="aspect-[4/3] w-full object-cover"
                            />
                        ) : (
                            <div className="flex aspect-[4/3] items-center justify-center text-sm text-slate-500">
                                No image selected
                            </div>
                        )}
                    </div>

                    {selectedImage ? (
                        <div className="absolute bottom-8 left-8 rounded-full bg-slate-950/70 px-3 py-1 text-xs font-medium text-white backdrop-blur">
                            Primary image for {productName}
                        </div>
                    ) : null}
                </div>
            </section>

            <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900">Gallery</h3>
                        <p className="mt-1 text-sm text-slate-600">
                            Click a thumbnail to preview it in the main frame.
                        </p>
                    </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-3">
                    {sortedImages.map((image, index) => {
                        const isSelected = index === selectedIndex;
                        const previewUrl = resolveProductImageUrl(image);

                        return (
                            <button
                                key={image.id}
                                type="button"
                                onClick={() => setSelectedIndex(index)}
                                aria-label={`Show product image ${image.position}`}
                                aria-pressed={index === activeIndex}
                                className={[
                                    "group overflow-hidden rounded-xl border bg-slate-50 text-left transition focus:outline-none focus:ring-2 focus:ring-slate-400",
                                    isSelected
                                        ? "border-slate-900 ring-2 ring-slate-900/10"
                                        : "border-slate-200 hover:border-slate-400",
                                ].join(" ")}
                            >
                                <div className="relative">
                                    {previewUrl ? (
                                        <img
                                            src={previewUrl}
                                            alt={`${productName} thumbnail ${image.position}`}
                                            className="aspect-square w-full object-cover transition duration-200 group-hover:scale-[1.02]"
                                        />
                                    ) : (
                                        <div className="flex aspect-square items-center justify-center text-xs text-slate-500">
                                            Missing preview
                                        </div>
                                    )}

                                    <div className="absolute left-2 top-2 rounded-full bg-slate-950/80 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                                        {image.position}
                                    </div>
                                </div>

                                <div className="border-t border-slate-200 bg-white px-3 py-2">
                                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                                        {isSelected ? "Selected" : `Image ${image.position}`}
                                    </p>
                                    <p className="mt-0.5 text-xs text-slate-600">
                                        {isSelected ? "Main preview" : "Click to preview"}
                                    </p>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </aside>
        </div>
    );
}
