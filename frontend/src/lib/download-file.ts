"use client";

export interface CsvDownloadResult {
    blob: Blob;
    filename: string;
    rowCount: number;
}

export function triggerBrowserDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
}

