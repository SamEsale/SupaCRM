"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

type ProtectedRouteProps = {
    children: ReactNode;
};

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
    const auth = useAuth();
    const router = useRouter();
    const [hasHydrated, setHasHydrated] = useState(false);

    useEffect(() => {
        const timer = window.setTimeout(() => {
            setHasHydrated(true);
        }, 0);

        return () => window.clearTimeout(timer);
    }, []);

    useEffect(() => {
        if (!hasHydrated || !auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated) {
            router.replace("/login");
        }
    }, [auth.isAuthenticated, auth.isReady, hasHydrated, router]);

    if (!hasHydrated || !auth.isReady) {
        return <div className="p-6 text-sm text-slate-600">Loading session...</div>;
    }

    if (!auth.isAuthenticated) {
        return <div className="p-6 text-sm text-slate-600">Loading session...</div>;
    }

    return <>{children}</>;
}
