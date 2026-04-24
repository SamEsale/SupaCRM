"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/hooks/use-auth";

interface ProtectedRouteProps {
    children: React.ReactNode;
}

function ProtectedRouteLoadingShell({
    title,
    description,
}: {
    title: string;
    description: string;
}) {
    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
            <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
                <p className="mt-2 text-sm text-slate-600">{description}</p>
            </div>
        </main>
    );
}

export default function ProtectedRoute({
    children,
}: ProtectedRouteProps) {
    const router = useRouter();
    const auth = useAuth();
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    useEffect(() => {
        if (isMounted && auth.isReady && !auth.isAuthenticated) {
            router.replace("/login");
        }
    }, [auth.isAuthenticated, auth.isReady, isMounted, router]);

    if (!isMounted || !auth.isReady) {
        return (
            <ProtectedRouteLoadingShell
                title="Loading session"
                description="Checking your authentication state."
            />
        );
    }

    if (!auth.isAuthenticated) {
        return (
            <ProtectedRouteLoadingShell
                title="Redirecting to login"
                description="Your session was not found."
            />
        );
    }

    return <>{children}</>;
}
