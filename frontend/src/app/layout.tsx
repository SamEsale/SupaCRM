import type { Metadata } from "next";
import { ToastProvider } from "@/components/feedback/ToastProvider";
import "./globals.css";

export const metadata: Metadata = {
    title: "SupaCRM",
    description: "Multi-tenant SaaS CRM",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="h-full antialiased">
            <body className="min-h-full bg-slate-100 text-slate-900">
                <ToastProvider>{children}</ToastProvider>
            </body>
        </html>
    );
}
