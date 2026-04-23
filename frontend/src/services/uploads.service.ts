import { apiClient } from "@/lib/api-client";

export type UploadPurpose = "product-image" | "tenant-logo";

export interface PresignedUploadRequest {
    purpose: UploadPurpose;
    file_name: string;
    content_type: string;
}

export interface PresignedUploadResponse {
    bucket: string;
    file_key: string;
    upload_url: string;
    download_url: string;
    expires_in_seconds: number;
}

export interface UploadObjectRequest {
    purpose: UploadPurpose;
    file_name: string;
    content_type: string;
    content_base64: string;
}

export interface UploadObjectResponse {
    bucket: string;
    file_key: string;
    file_url: string;
}

export async function createPresignedUploadTarget(
    payload: PresignedUploadRequest,
): Promise<PresignedUploadResponse> {
    const response = await apiClient.post<PresignedUploadResponse>("/storage/uploads/presign", payload);
    return response.data;
}

function uint8ArrayToBase64(bytes: Uint8Array): string {
    const chunkSize = 0x8000;
    let binary = "";

    for (let index = 0; index < bytes.length; index += chunkSize) {
        const chunk = bytes.subarray(index, index + chunkSize);
        binary += String.fromCharCode(...chunk);
    }

    return window.btoa(binary);
}

async function fileToBase64(file: File): Promise<string> {
    const buffer = await file.arrayBuffer();
    return uint8ArrayToBase64(new Uint8Array(buffer));
}

export async function uploadFileToStorage(
    file: File,
    purpose: UploadPurpose,
): Promise<UploadObjectResponse> {
    const contentBase64 = await fileToBase64(file);
    const response = await apiClient.post<UploadObjectResponse>("/storage/uploads", {
        purpose,
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
        content_base64: contentBase64,
    } satisfies UploadObjectRequest);
    return response.data;
}
