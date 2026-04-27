"use client";

import { useRef, useState } from "react";

import { MAX_PRODUCT_IMAGES } from "@/components/products/product-image-rules";
import {
    createReorderedProductImages,
    normalizeProductImageInputs,
    resolveProductImageUrl,
} from "@/components/products/product-image-utils";
import { uploadFileToStorage } from "@/services/uploads.service";
import type { ProductImageInput } from "@/types/product";

type ProductImageEditorProps = {
    images: ProductImageInput[];
    onChange: (images: ProductImageInput[]) => void;
};

function createBlankImage(position: number): ProductImageInput {
    return {
        position,
        file_key: "",
        file_url: null,
    };
}

export default function ProductImageEditor({
    images,
    onChange,
}: ProductImageEditorProps) {
    const fileInputRefs = useRef<Array<HTMLInputElement | null>>([]);
    const [uploadingPositions, setUploadingPositions] = useState<Record<number, boolean>>({});
    const [uploadError, setUploadError] = useState<string>("");
    const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

    async function handleFileSelection(index: number, file: File | null): Promise<void> {
        if (!file) {
            return;
        }

        setUploadError("");
        setUploadingPositions((current) => ({ ...current, [index]: true }));

        try {
            const uploaded = await uploadFileToStorage(file, "product-image");

            const nextImages = images.map((image, currentIndex) =>
                currentIndex === index
                    ? {
                        ...image,
                        file_key: uploaded.file_key,
                        file_url: resolveProductImageUrl({
                            file_key: uploaded.file_key,
                            file_url: uploaded.file_url ?? null,
                        }),
                    }
                    : image,
            );

            onChange(normalizeProductImageInputs(nextImages));
        } catch (error) {
            console.error("Failed to upload product image:", error);
            setUploadError("The image could not be uploaded. Please try again.");
        } finally {
            setUploadingPositions((current) => ({ ...current, [index]: false }));
        }
    }

    function addImage(): void {
        if (images.length >= MAX_PRODUCT_IMAGES) {
            return;
        }

        onChange(normalizeProductImageInputs([...images, createBlankImage(images.length + 1)]));
    }

    function removeImage(index: number): void {
        const nextImages = images.filter((_, currentIndex) => currentIndex !== index);
        onChange(normalizeProductImageInputs(nextImages));
    }

    function moveImage(index: number, direction: -1 | 1): void {
        const targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= images.length) {
            return;
        }

        onChange(
            normalizeProductImageInputs(
                createReorderedProductImages(images, index, targetIndex),
            ),
        );
    }

    function handleDragStart(index: number, event: React.DragEvent<HTMLButtonElement>): void {
        setDraggedIndex(index);
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(index));
    }

    function handleDrop(targetIndex: number): void {
        if (draggedIndex === null || draggedIndex === targetIndex) {
            setDraggedIndex(null);
            return;
        }

        onChange(
            normalizeProductImageInputs(
                createReorderedProductImages(images, draggedIndex, targetIndex),
            ),
        );
        setDraggedIndex(null);
    }

    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h3 className="text-lg font-semibold text-slate-900">Product images</h3>
                    <p className="mt-1 text-sm text-slate-600">
                        Upload product images, then drag or move them to set the primary image order.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={addImage}
                    disabled={images.length >= MAX_PRODUCT_IMAGES}
                    aria-label="Add image"
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    Add image
                </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                <span>
                    {images.length} / {MAX_PRODUCT_IMAGES} images
                </span>
                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">
                    Image 1 is the primary image
                </span>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
                {images.map((image, index) => {
                    const previewUrl = resolveProductImageUrl(image);
                    const isPrimary = index === 0;
                    const isDragging = draggedIndex === index;

                    return (
                        <article
                            key={`${image.position}-${index}`}
                            onDragOver={(event) => {
                                event.preventDefault();
                            }}
                            onDrop={(event) => {
                                event.preventDefault();
                                handleDrop(index);
                            }}
                            className={[
                                "rounded-2xl border bg-slate-50 p-4 shadow-sm transition",
                                isPrimary
                                    ? "border-amber-300 ring-1 ring-amber-200"
                                    : "border-slate-200",
                                isDragging ? "opacity-70" : "",
                            ].join(" ")}
                        >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="flex items-center gap-3">
                                    <button
                                        type="button"
                                        draggable
                                        onDragStart={(event) => handleDragStart(index, event)}
                                        onDragEnd={() => setDraggedIndex(null)}
                                        aria-label={`Drag image ${index + 1} to reorder`}
                                        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-500 transition hover:border-slate-400 hover:text-slate-700"
                                    >
                                        <span aria-hidden="true">⋮⋮</span>
                                    </button>

                                    <div>
                                        <p className="text-sm font-semibold text-slate-900">
                                            Image {index + 1}
                                        </p>
                                        <p className="text-xs text-slate-500">
                                            {isPrimary
                                                ? "Primary image"
                                                : "Secondary image"}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    <button
                                        type="button"
                                        onClick={() => moveImage(index, -1)}
                                        disabled={index === 0}
                                        aria-label={`Move image ${index + 1} left`}
                                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Move left
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => moveImage(index, 1)}
                                        disabled={index === images.length - 1}
                                        aria-label={`Move image ${index + 1} right`}
                                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Move right
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => removeImage(index)}
                                        aria-label={`Remove image ${index + 1}`}
                                        className="rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50"
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>

                            <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
                                {previewUrl ? (
                                    <img
                                        src={previewUrl}
                                        alt={`Product image ${index + 1}`}
                                        className="aspect-square w-full object-cover"
                                    />
                                ) : (
                                    <div className="flex aspect-square items-center justify-center bg-slate-100 text-sm text-slate-500">
                                        Upload an image to preview it here.
                                    </div>
                                )}
                            </div>

                            <div className="mt-4 flex flex-wrap gap-2">
                                <input
                                    ref={(element) => {
                                        fileInputRefs.current[index] = element;
                                    }}
                                    id={`product-image-upload-${image.position}`}
                                    type="file"
                                    accept="image/*"
                                    aria-label={`Upload image ${index + 1}`}
                                    className="sr-only"
                                    onChange={(event) => {
                                        void handleFileSelection(
                                            index,
                                            event.target.files?.[0] ?? null,
                                        );
                                        event.target.value = "";
                                    }}
                                />

                                <button
                                    type="button"
                                    onClick={() => fileInputRefs.current[index]?.click()}
                                    aria-label={`Choose file for image ${index + 1}`}
                                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
                                >
                                    {uploadingPositions[index] ? "Uploading..." : "Upload image"}
                                </button>

                                <p className="self-center text-xs text-slate-500">
                                    Drag the handle or use the move buttons to change order.
                                </p>
                            </div>
                        </article>
                    );
                })}
            </div>

            {uploadError ? (
                <p className="mt-4 text-sm text-red-700">{uploadError}</p>
            ) : null}
        </section>
    );
}
