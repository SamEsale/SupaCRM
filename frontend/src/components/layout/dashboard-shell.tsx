"use client";

import LogoutButton from "@/components/auth/logout-button";
import Sidebar from "@/components/navigation/Sidebar";
import { useAuth } from "@/hooks/use-auth";

interface DashboardShellProps {
    children: React.ReactNode;
}

export default function DashboardShell({
    children,
}: DashboardShellProps) {
    const auth = useAuth();

    if (!auth.isReady) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
                <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
                    <h1 className="text-xl font-semibold text-slate-900">
                        Loading dashboard
                    </h1>
                    <p className="mt-2 text-sm text-slate-600">
                        Preparing your workspace.
                    </p>
                </div>
            </main>
        );
    }

    return (
        <div className="flex min-h-screen flex-col bg-slate-100">
            <header className="border-b border-slate-200 bg-white">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900">SupaCRM</h1>
                        <p className="text-sm text-slate-600">
                            {auth.user?.email ?? "Authenticated user"}
                        </p>
                    </div>

                    <LogoutButton />
                </div>
            </header>

            <div className="flex flex-1">
                <Sidebar />

                <main className="flex-1 overflow-x-auto p-6">
                    <div className="mx-auto max-w-7xl">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
