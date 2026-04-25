"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { resolveStoredMediaUrl } from "@/services/media-url";
import { notifyTenantBrandingChanged } from "@/services/tenant-branding-events";
import { uploadFileToStorage } from "@/services/uploads.service";
import {
    getTenantBranding,
    updateTenantBranding,
} from "@/services/tenant-branding.service";
import type { TenantBranding } from "@/types/settings";

function getErrorMessage(error: unknown): string {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (typeof response?.data?.detail === "string" && response.data.detail.trim().length > 0) {
            return response.data.detail;
        }
    }

    if (error instanceof Error && error.message.trim().length > 0) {
        return error.message;
    }

    return "Failed to update branding.";
}

export default function BrandingLogoCard() {
    const auth = useAuth();
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [branding, setBranding] = useState<TenantBranding | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [isUploading, setIsUploading] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");

    useEffect(() => {
        if (!auth.isReady) {
            return;
        }

        if (!auth.isAuthenticated || !auth.accessToken) {
            setIsLoading(false);
            return;
        }

        let isMounted = true;

        async function loadBranding(): Promise<void> {
            try {
                setIsLoading(true);
                setErrorMessage("");
                const response = await getTenantBranding();
                if (isMounted) {
                    setBranding(response);
                }
            } catch (error) {
                console.error("Failed to load branding:", error);
                if (isMounted) {
                    setErrorMessage(getErrorMessage(error));
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        void loadBranding();

        return () => {
            isMounted = false;
        };
    }, [auth.accessToken, auth.isAuthenticated, auth.isReady]);

    async function handleUpload(file: File | null): Promise<void> {
        if (!file) {
            return;
        }

        try {
            setIsUploading(true);
            setErrorMessage("");
            setSuccessMessage("");

            const uploaded = await uploadFileToStorage(file, "tenant-logo");

            setIsSaving(true);
            const updated = await updateTenantBranding({
                logo_file_key: uploaded.file_key,
            });
            setBranding(updated);
            notifyTenantBrandingChanged();
            setSuccessMessage("Company logo updated.");
        } catch (error) {
            console.error("Failed to upload tenant logo:", error);
            setErrorMessage(getErrorMessage(error));
        } finally {
            setIsUploading(false);
            setIsSaving(false);
        }
    }

    async function handleRemove(): Promise<void> {
        try {
            setIsSaving(true);
            setErrorMessage("");
            setSuccessMessage("");
            const updated = await updateTenantBranding({ logo_file_key: null });
            setBranding(updated);
            notifyTenantBrandingChanged();
            setSuccessMessage("Company logo removed.");
        } catch (error) {
            console.error("Failed to remove tenant logo:", error);
            setErrorMessage(getErrorMessage(error));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="text-xl font-semibold text-slate-900">Company Branding</h2>
                    <p className="mt-1 text-sm text-slate-600">
                        Upload the tenant/company logo used in launch-facing surfaces.
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        aria-label="Upload company logo"
                        className="sr-only"
                        onChange={(event) => {
                            void handleUpload(event.target.files?.[0] ?? null);
                            event.target.value = "";
                        }}
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isLoading || isUploading || isSaving}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isUploading ? "Uploading..." : "Upload logo"}
                    </button>
                    <button
                        type="button"
                        onClick={() => void handleRemove()}
                        disabled={isLoading || isUploading || isSaving || !branding?.logo_file_key}
                        className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Remove logo
                    </button>
                </div>
            </div>

            {isLoading ? (
                <p className="mt-4 text-sm text-slate-600">Loading branding settings...</p>
            ) : (
                <div className="mt-4 grid gap-4 md:grid-cols-[240px_1fr]">
                    <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                        {resolveStoredMediaUrl(branding) ? (
                            <img
                                src={resolveStoredMediaUrl(branding) ?? ""}
                                alt="Tenant logo preview"
                                className="h-48 w-full object-cover"
                            />
                        ) : (
                            <div className="flex h-48 items-center justify-center px-4 text-center text-sm text-slate-500">
                                No logo uploaded yet.
                            </div>
                        )}
                    </div>

                    <div className="space-y-3">
                        <p className="text-sm text-slate-700">
                            Current file key:{" "}
                            <span className="font-mono text-xs break-all">
                                {branding?.logo_file_key ?? "not set"}
                            </span>
                        </p>
                        <p className="text-sm text-slate-600">
                            Uploading a new logo replaces the current one. This setting is stored against the tenant and is used across the launch-ready product surfaces.
                        </p>
                        {errorMessage ? (
                            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                {errorMessage}
                            </p>
                        ) : null}
                        {successMessage ? (
                            <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                                {successMessage}
                            </p>
                        ) : null}
                    </div>
                </div>
            )}
        </section>
    );
}
