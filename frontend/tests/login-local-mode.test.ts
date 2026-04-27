import { describe, expect, it } from "vitest";

import { isLocalLoginHost } from "@/components/auth/login-mode";
import { buildLoginRequestPayload } from "@/components/auth/login-payload";

describe("local login mode", () => {
    it("detects localhost login hosts", () => {
        expect(isLocalLoginHost("localhost")).toBe(true);
        expect(isLocalLoginHost("localhost:3000")).toBe(true);
        expect(isLocalLoginHost("127.0.0.1")).toBe(true);
        expect(isLocalLoginHost("127.0.0.1:3000")).toBe(true);
        expect(isLocalLoginHost("::1")).toBe(true);
        expect(isLocalLoginHost("example.com")).toBe(false);
    });

    it("omits tenant_id from the local login payload when the field is empty", () => {
        const payload = buildLoginRequestPayload({
            isLocalLogin: true,
            tenantId: "",
            email: "supacrm@test.com",
            password: "AdminTest123!",
        });

        expect(payload).toEqual({
            email: "supacrm@test.com",
            password: "AdminTest123!",
        });
        expect("tenant_id" in payload).toBe(false);
    });

    it("includes tenant_id when a tenant is provided or local mode is off", () => {
        expect(
            buildLoginRequestPayload({
                isLocalLogin: true,
                tenantId: "supacrm-test",
                email: "supacrm@test.com",
                password: "AdminTest123!",
            }),
        ).toEqual({
            tenant_id: "supacrm-test",
            email: "supacrm@test.com",
            password: "AdminTest123!",
        });

        expect(
            buildLoginRequestPayload({
                isLocalLogin: false,
                tenantId: "supacrm-test",
                email: "supacrm@test.com",
                password: "AdminTest123!",
            }),
        ).toEqual({
            tenant_id: "supacrm-test",
            email: "supacrm@test.com",
            password: "AdminTest123!",
        });
    });
});
