import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";

import { getApiErrorCode, getApiErrorMessage, getApiErrorStatus, isAuthorizationError } from "@/lib/api-errors";

function buildAxiosError(
    status: number,
    data: unknown,
): AxiosError {
    return new AxiosError(
        "Request failed",
        "ERR_BAD_REQUEST",
        undefined,
        undefined,
        {
            status,
            statusText: "Error",
            headers: {},
            config: { headers: new AxiosHeaders() },
            data,
        },
    );
}

describe("api error utils", () => {
    it("reads the standardized backend error envelope", () => {
        const error = buildAxiosError(403, {
            error: {
                code: "forbidden",
                message: "You do not have permission to perform this action.",
            },
        });

        expect(getApiErrorStatus(error)).toBe(403);
        expect(getApiErrorCode(error)).toBe("forbidden");
        expect(getApiErrorMessage(error, "fallback")).toBe(
            "You do not have permission to perform this action.",
        );
        expect(isAuthorizationError(error)).toBe(true);
    });

    it("falls back to legacy detail payloads for older mocks and routes", () => {
        const error = buildAxiosError(400, {
            detail: "Legacy detail response",
        });

        expect(getApiErrorMessage(error, "fallback")).toBe("Legacy detail response");
    });
});
