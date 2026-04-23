import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const rootDir = dirname(fileURLToPath(import.meta.url));

process.env.NEXT_PUBLIC_API_BASE_URL ??= "http://127.0.0.1:3000";

export default defineConfig({
    resolve: {
        alias: {
            "@": resolve(rootDir, "src"),
        },
    },
    test: {
        environment: "jsdom",
        restoreMocks: true,
        clearMocks: true,
    },
});
