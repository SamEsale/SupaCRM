"use client";

import BrandingLogoCard from "@/components/settings/BrandingLogoCard";
import SettingsPageFrame from "@/components/settings/SettingsPageFrame";

export default function BrandingSettingsPage() {
    return (
        <SettingsPageFrame
            title="Branding"
            description="Manage the tenant/company logo used across the current launch-ready product surfaces."
        >
            <BrandingLogoCard />
        </SettingsPageFrame>
    );
}
