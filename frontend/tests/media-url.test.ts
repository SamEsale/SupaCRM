import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/constants/env";
import {
    resolveMediaUrl,
    resolveStoredMediaUrl,
} from "@/services/media-url";

describe("media url resolution", () => {
    it("resolves absolute urls, backend-relative urls, and stored file keys", () => {
        expect(resolveMediaUrl("https://cdn.example.com/logo.png")).toBe(
            "https://cdn.example.com/logo.png",
        );
        expect(resolveMediaUrl("/media/product-images/tenant-1/image.png")).toBe(
            new URL("/media/product-images/tenant-1/image.png", API_BASE_URL).toString(),
        );
        expect(
            resolveStoredMediaUrl({
                file_url: null,
                file_key: "product-images/tenant-1/image.png",
            }),
        ).toBe(new URL("/media/product-images/tenant-1/image.png", API_BASE_URL).toString());
    });

    it("prefers the local media path for stored records in development when a file key exists", () => {
        expect(
            resolveStoredMediaUrl({
                file_url: "https://minio.internal.example/object",
                file_key: "tenant-logos/tenant-1/logo.png",
            }),
        ).toBe(new URL("/media/tenant-logos/tenant-1/logo.png", API_BASE_URL).toString());
    });
});
