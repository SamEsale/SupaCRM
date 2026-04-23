"use client";

import axios, { type AxiosError } from "axios";

type ApiErrorEnvelope = {
    error?: {
        code?: unknown;
        message?: unknown;
        details?: unknown;
    };
    detail?: unknown;
    message?: unknown;
};

function getResponsePayload(error: unknown): ApiErrorEnvelope | null {
    if (axios.isAxiosError(error)) {
        const data = error.response?.data;
        if (typeof data === "object" && data !== null) {
            return data as ApiErrorEnvelope;
        }
    }

    if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof error.response === "object" &&
        error.response !== null &&
        "data" in error.response &&
        typeof error.response.data === "object" &&
        error.response.data !== null
    ) {
        return error.response.data as ApiErrorEnvelope;
    }

    return null;
}

export function getApiErrorStatus(error: unknown): number | null {
    if (axios.isAxiosError(error)) {
        return error.response?.status ?? null;
    }

    if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof error.response === "object" &&
        error.response !== null &&
        "status" in error.response &&
        typeof error.response.status === "number"
    ) {
        return error.response.status;
    }

    return null;
}

export function getApiErrorCode(error: unknown): string | null {
    const payload = getResponsePayload(error);
    const code = payload?.error?.code;
    return typeof code === "string" && code.trim().length > 0 ? code : null;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
    const payload = getResponsePayload(error);

    const normalizedMessage = payload?.error?.message;
    if (typeof normalizedMessage === "string" && normalizedMessage.trim().length > 0) {
        return normalizedMessage;
    }

    const legacyDetail = payload?.detail;
    if (typeof legacyDetail === "string" && legacyDetail.trim().length > 0) {
        return legacyDetail;
    }

    const topLevelMessage = payload?.message;
    if (typeof topLevelMessage === "string" && topLevelMessage.trim().length > 0) {
        return topLevelMessage;
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return fallback;
}

export function isAuthorizationError(error: unknown): boolean {
    const status = getApiErrorStatus(error);
    return status === 401 || status === 403;
}

export function applyNormalizedApiErrorMessage(error: AxiosError): AxiosError {
    const message = getApiErrorMessage(error, error.message || "Request failed.");
    if (message && message !== error.message) {
        error.message = message;
    }
    return error;
}
