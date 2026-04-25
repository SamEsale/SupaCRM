import LoginForm from "@/components/auth/login-form";
import { headers } from "next/headers";
import { isLocalLoginHost } from "@/components/auth/login-mode";

export default async function LoginPage() {
    const hostHeaders = await headers();
    const host = hostHeaders.get("host") ?? undefined;
    const isLocalLogin = isLocalLoginHost(host);

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
            <LoginForm isLocalLogin={isLocalLogin} />
        </main>
    );
}
