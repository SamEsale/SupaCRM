import { API_BASE_URL } from "@/constants/env";

const isProduction = process.env.NODE_ENV === "production";

export function resolveMediaUrl(url: string | null | undefined): string | null {
    if (!url) {
        return null;
    }

    if (/^https?:\/\//i.test(url)) {
        return url;
    }

    const normalizedPath = url.startsWith("/") ? url : `/${url}`;
    return new URL(normalizedPath, API_BASE_URL).toString();
}

export interface StoredMediaSource {
    file_url?: string | null;
    file_key?: string | null;
}

export interface TenantBrandMediaSource {
    logo_url?: string | null;
    logo_file_key?: string | null;
}

type MediaSource = StoredMediaSource | TenantBrandMediaSource;

export function resolveStoredMediaUrl(
    media: MediaSource | null | undefined,
): string | null {
    const rawFileKey = media
        ? "file_key" in media
            ? media.file_key
            : "logo_file_key" in media
                ? media.logo_file_key
                : null
        : null;
    const trimmedFileKey = rawFileKey?.trim();
    const rawFileUrl = media
        ? "file_url" in media
            ? media.file_url
            : "logo_url" in media
                ? media.logo_url
                : null
        : null;

    if (!isProduction && trimmedFileKey) {
        return resolveMediaUrl(`/media/${trimmedFileKey}`);
    }

    const resolvedUrl = resolveMediaUrl(rawFileUrl);
    if (resolvedUrl) {
        return resolvedUrl;
    }

    if (!trimmedFileKey) {
        return null;
    }

    return resolveMediaUrl(`/media/${trimmedFileKey}`);
}

export function resolveMediaPreviewUrl(
    url: string | null | undefined,
    fileKey: string | null | undefined = null,
): string | null {
    return resolveStoredMediaUrl({ file_url: url, file_key: fileKey });
}
