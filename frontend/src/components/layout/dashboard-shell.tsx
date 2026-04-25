"use client";

import { useEffect, useState } from "react";

import LogoutButton from "@/components/auth/logout-button";
import Sidebar from "@/components/navigation/Sidebar";
import TenantBrandBlock from "@/components/navigation/TenantBrandBlock";
import { useAuth } from "@/hooks/use-auth";
import { applyTenantTheme, resolveTenantTheme } from "@/lib/tenant-theme";
import { TENANT_BRANDING_CHANGED_EVENT } from "@/services/tenant-branding-events";
import { getTenantBranding } from "@/services/tenant-branding.service";
import type { TenantBranding } from "@/types/settings";

interface DashboardShellProps {
    children: React.ReactNode;
}

export default function DashboardShell({
    children,
}: DashboardShellProps) {
    const auth = useAuth();
    const [branding, setBranding] = useState<TenantBranding | null>(null);
    const visibleBranding = auth.isAuthenticated ? branding : null;

    useEffect(() => {
        applyTenantTheme(resolveTenantTheme(visibleBranding));
    }, [visibleBranding]);

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            return;
        }

        let isMounted = true;

        async function loadBranding(): Promise<void> {
            try {
                const response = await getTenantBranding();
                if (isMounted) {
                    setBranding(response);
                }
            } catch (error) {
                console.error("Failed to load tenant branding:", error);
                if (isMounted) {
                    setBranding(null);
                }
            }
        }

        void loadBranding();

        function handleBrandingChanged(): void {
            void loadBranding();
        }

        window.addEventListener(TENANT_BRANDING_CHANGED_EVENT, handleBrandingChanged);

        return () => {
            isMounted = false;
            window.removeEventListener(
                TENANT_BRANDING_CHANGED_EVENT,
                handleBrandingChanged,
            );
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady, auth.user?.tenant_id]);

    return (
        <div className="flex min-h-screen flex-col bg-slate-100">
            <header className="border-b border-slate-200 bg-white">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                    <TenantBrandBlock
                        branding={visibleBranding}
                        subtitle={auth.user?.email ?? "Authenticated user"}
                    />

                    <LogoutButton />
                </div>
            </header>

            <div className="flex flex-1">
                <Sidebar branding={visibleBranding} />

                <main className="flex-1 overflow-x-auto p-6">
                    <div className="mx-auto max-w-7xl">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
