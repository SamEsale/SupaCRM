"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type ToastVariant = "success" | "error" | "warning" | "info";

type ToastRecord = {
    id: number;
    message: string;
    variant: ToastVariant;
};

type NotifyInput = {
    message: string;
    variant?: ToastVariant;
};

type ToastContextValue = {
    notify: (input: NotifyInput) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    warning: (message: string) => void;
    info: (message: string) => void;
};

const noop = () => undefined;

const ToastContext = createContext<ToastContextValue>({
    notify: noop,
    success: noop,
    error: noop,
    warning: noop,
    info: noop,
});

const TOAST_STYLES: Record<ToastVariant, string> = {
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    error: "border-red-200 bg-red-50 text-red-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    info: "border-slate-200 bg-white text-slate-900",
};

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<ToastRecord[]>([]);

    const dismiss = useCallback((id: number) => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
    }, []);

    const notify = useCallback(
        ({ message, variant = "info" }: NotifyInput) => {
            const nextToast: ToastRecord = {
                id: Date.now() + Math.floor(Math.random() * 1000),
                message,
                variant,
            };

            setToasts((current) => [...current, nextToast]);

            window.setTimeout(() => {
                dismiss(nextToast.id);
            }, 4500);
        },
        [dismiss],
    );

    const value = useMemo<ToastContextValue>(
        () => ({
            notify,
            success: (message: string) => notify({ message, variant: "success" }),
            error: (message: string) => notify({ message, variant: "error" }),
            warning: (message: string) => notify({ message, variant: "warning" }),
            info: (message: string) => notify({ message, variant: "info" }),
        }),
        [notify],
    );

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-3">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`pointer-events-auto rounded-xl border px-4 py-3 text-sm shadow-lg ${TOAST_STYLES[toast.variant]}`}
                        role="status"
                        aria-live="polite"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <p>{toast.message}</p>
                            <button
                                type="button"
                                onClick={() => dismiss(toast.id)}
                                className="rounded-md px-2 py-1 text-xs font-medium text-current/70 transition hover:bg-black/5 hover:text-current"
                            >
                                Dismiss
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast(): ToastContextValue {
    return useContext(ToastContext);
}
