import { resolveStoredMediaUrl } from "@/services/media-url";
import type { ProductImage, ProductImageInput } from "@/types/product";

type ProductImageLike = {
    position: number;
    file_key: string;
    file_url?: string | null;
};

export function sortProductImagesByPosition<T extends ProductImageLike>(
    images: readonly T[],
): T[] {
    return [...images].sort((left, right) => left.position - right.position);
}

export function normalizeProductImageInputs(
    images: ProductImageInput[],
): ProductImageInput[] {
    return images.map((image, index) => ({
        position: index + 1,
        file_key: image.file_key,
        file_url: image.file_url ?? null,
    }));
}

export function createReorderedProductImages<T extends ProductImageLike>(
    images: readonly T[],
    fromIndex: number,
    toIndex: number,
): T[] {
    if (fromIndex === toIndex) {
        return [...images];
    }

    const nextImages = [...images];
    const [movedImage] = nextImages.splice(fromIndex, 1);
    nextImages.splice(toIndex, 0, movedImage);

    return nextImages.map((image, index) => ({
        ...image,
        position: index + 1,
    }));
}

export function resolveProductImageUrl(
    image: Pick<ProductImage, "file_key" | "file_url"> | ProductImageInput,
): string | null {
    return resolveStoredMediaUrl(image);
}
