"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

import { getCurrentUser, login } from "@/services/auth.service";
import {
    setAuthStorage,
    setTenantId,
    setTokenStorage,
} from "@/lib/auth-storage";

interface LoginFormProps {
    isLocalLogin?: boolean;
}

interface LoginFormState {
    email: string;
    password: string;
}

const initialState: LoginFormState = {
    email: "",
    password: "",
};

function extractApiMessage(value: unknown): string | null {
    if (typeof value === "string" && value.trim().length > 0) {
        return value;
    }

    if (Array.isArray(value)) {
        for (const item of value) {
            const message = extractApiMessage(item);
            if (message) {
                return message;
            }
        }
        return null;
    }

    if (typeof value === "object" && value !== null) {
        const record = value as Record<string, unknown>;
        return (
            extractApiMessage(record.detail) ||
            extractApiMessage(record.message) ||
            extractApiMessage(record.error) ||
            extractApiMessage(record.msg)
        );
    }

    return null;
}

function getErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null) {
        const response = (error as { response?: { data?: unknown } }).response;
        const responseMessage = extractApiMessage(response?.data);
        if (responseMessage) {
            return responseMessage;
        }
    }

    if (axios.isAxiosError(error)) {
        return extractApiMessage(error.response?.data) || "Login request failed.";
    }

    return extractApiMessage(error) || "An unexpected error occurred.";
}

export default function LoginForm(_props: LoginFormProps = {}) {
    const router = useRouter();

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
            const tokenResponse = await login({
                email: form.email.trim(),
                password: form.password,
            });

            setTenantId(tokenResponse.tenant_id);

            setTokenStorage(
                tokenResponse.access_token,
                tokenResponse.refresh_token,
            );

            const currentUser = await getCurrentUser(tokenResponse.tenant_id);

            setAuthStorage(
                tokenResponse.access_token,
                tokenResponse.refresh_token,
                currentUser,
            );

            router.push("/dashboard");
            router.refresh();
        } catch (error: unknown) {
            setErrorMessage(getErrorMessage(error));
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
                        placeholder="Enter your email"
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
        </div>
    );
}
