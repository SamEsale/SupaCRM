"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { clearAuthStorage, getRefreshToken } from "@/lib/auth-storage";
import { logout } from "@/services/auth.service";

export default function LogoutButton() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleLogout(): Promise<void> {
        setIsSubmitting(true);

        try {
            const refreshToken = getRefreshToken();

            if (refreshToken) {
                await logout({
                    refresh_token: refreshToken,
                    revoke_family: false,
                });
            }
        } catch {
            // Ignore logout API failures and still clear local session.
        } finally {
            clearAuthStorage();
            router.push("/login");
            router.refresh();
            setIsSubmitting(false);
        }
    }

    return (
        <button
            type="button"
            onClick={handleLogout}
            disabled={isSubmitting}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
            {isSubmitting ? "Signing out..." : "Sign out"}
        </button>
    );
}