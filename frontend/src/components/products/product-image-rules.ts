import type { ProductImageInput } from "@/types/product";

export const MIN_PRODUCT_IMAGES = 3;
export const MAX_PRODUCT_IMAGES = 15;

export function validateProductImageCount(
    images: ProductImageInput[],
): string | null {
    if (images.length < MIN_PRODUCT_IMAGES) {
        return `At least ${MIN_PRODUCT_IMAGES} product images are required.`;
    }

    if (images.length > MAX_PRODUCT_IMAGES) {
        return `No more than ${MAX_PRODUCT_IMAGES} product images are allowed.`;
    }

    return null;
}

export function validateProductImageCollection(
    images: ProductImageInput[],
): string | null {
    const countError = validateProductImageCount(images);
    if (countError) {
        return countError;
    }

    for (const [index, image] of images.entries()) {
        if (!image.file_key.trim()) {
            return `Image ${index + 1} file key is required.`;
        }
    }

    return null;
}
