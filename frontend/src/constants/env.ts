const rawApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!rawApiBaseUrl) {
    throw new Error(
        "Missing NEXT_PUBLIC_API_BASE_URL. Set it in frontend/.env.local or the frontend runtime environment.",
    );
}

export const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, "");
