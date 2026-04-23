"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

import { getCurrentUser, login } from "@/services/auth.service";
import { useToast } from "@/components/feedback/ToastProvider";
import {
    setAuthStorage,
    setTenantId,
    setTokenStorage,
} from "@/lib/auth-storage";
import { buildLoginRequestPayload } from "@/components/auth/login-payload";
import { getApiErrorMessage } from "@/lib/api-errors";

interface LoginFormState {
    tenantId: string;
    email: string;
    password: string;
}

interface LoginFormProps {
    isLocalLogin: boolean;
}

const initialState: LoginFormState = {
    tenantId: "",
    email: "",
    password: "",
};

function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        return getApiErrorMessage(error, "Login request failed.");
    }

    const normalizedMessage = getApiErrorMessage(error, "");
    if (normalizedMessage.trim().length > 0) {
        return normalizedMessage;
    }

    if (error instanceof Error) {
        return error.message;
    }

    return "An unexpected error occurred.";
}

export default function LoginForm({ isLocalLogin }: LoginFormProps) {
    const router = useRouter();
    const toast = useToast();
    const [form, setForm] = useState<LoginFormState>(initialState);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");

    function handleChange(event: React.ChangeEvent<HTMLInputElement>): void {
        const { name, value } = event.target;

        setForm((prev) => ({
            ...prev,
            [name]: value,
        }));
    }

    async function handleSubmit(
        event: React.FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();
        setErrorMessage("");
        setIsSubmitting(true);

        try {
            const loginPayload = buildLoginRequestPayload({
                isLocalLogin,
                tenantId: form.tenantId,
                email: form.email,
                password: form.password,
            });
            const tokenResponse = await login(loginPayload);

            const resolvedTenantId =
                tokenResponse.tenant_id || loginPayload.tenant_id || "";
            if (!resolvedTenantId) {
                throw new Error("Tenant ID could not be resolved for this login.");
            }

            setTenantId(resolvedTenantId);

            setTokenStorage(
                tokenResponse.access_token,
                tokenResponse.refresh_token,
            );

            const currentUser = await getCurrentUser(resolvedTenantId);

            setAuthStorage(
                tokenResponse.access_token,
                tokenResponse.refresh_token,
                currentUser,
            );

            router.push("/dashboard");
            router.refresh();
        } catch (error: unknown) {
            const message = getErrorMessage(error);
            setErrorMessage(message);
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
            <h1 className="text-2xl font-bold text-slate-900">Login</h1>

            <p className="mt-2 text-sm text-slate-600">
                Sign in to SupaCRM with your email and password.
            </p>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                {!isLocalLogin ? (
                    <div>
                        <label
                            htmlFor="tenantId"
                            className="mb-1 block text-sm font-medium text-slate-700"
                        >
                            Tenant ID
                        </label>
                        <input
                            id="tenantId"
                            name="tenantId"
                            type="text"
                            value={form.tenantId}
                            onChange={handleChange}
                            placeholder="Enter tenant id"
                            autoComplete="organization"
                            required
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                        />
                    </div>
                ) : (
                    <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                        Local development login resolves the tenant from your email automatically.
                    </p>
                )}

                <div>
                    <label
                        htmlFor="email"
                        className="mb-1 block text-sm font-medium text-slate-700"
                    >
                        Email
                    </label>
                    <input
                        id="email"
                        name="email"
                        type="email"
                        value={form.email}
                        onChange={handleChange}
                        placeholder="Enter email"
                        autoComplete="email"
                        required
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />
                </div>

                <div>
                    <label
                        htmlFor="password"
                        className="mb-1 block text-sm font-medium text-slate-700"
                    >
                        Password
                    </label>
                    <input
                        id="password"
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                        placeholder="Enter password"
                        autoComplete="current-password"
                        required
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                    />
                </div>

                {errorMessage ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                        {errorMessage}
                    </div>
                ) : null}

                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {isSubmitting ? "Signing in..." : "Sign in"}
                </button>
            </form>

            <p className="mt-4 text-sm text-slate-600">
                Need a new workspace?{" "}
                <Link href="/register" className="font-medium text-slate-900 underline underline-offset-4">
                    Start here
                </Link>
            </p>
        </div>
    );
}
