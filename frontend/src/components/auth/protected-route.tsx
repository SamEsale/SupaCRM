"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";

interface ProtectedRouteProps {
    children: React.ReactNode;
}

export default function ProtectedRoute({
    children,
}: ProtectedRouteProps) {
    const router = useRouter();
    const auth = useAuth();

    useEffect(() => {
        if (auth.isReady && !auth.isAuthenticated) {
            router.replace("/login");
        }
    }, [auth.isAuthenticated, auth.isReady, router]);

    if (!auth.isReady) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
                <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h1 className="text-xl font-semibold text-slate-900">
                        Loading session
                    </h1>
                    <p className="mt-2 text-sm text-slate-600">
                        Checking your authentication state.
                    </p>
                </div>
            </main>
        );
    }

    if (!auth.isAuthenticated) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
                <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h1 className="text-xl font-semibold text-slate-900">
                        Redirecting to login
                    </h1>
                    <p className="mt-2 text-sm text-slate-600">
                        Your session was not found.
                    </p>
                </div>
            </main>
        );
    }

    return <>{children}</>;
}