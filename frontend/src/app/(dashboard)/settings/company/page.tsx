import CompanySettingsForm from "@/components/settings/CompanySettingsForm";
import SettingsPageFrame from "@/components/settings/SettingsPageFrame";

export default function CompanySettingsPage() {
    return (
        <SettingsPageFrame
            title="Company"
            description="Manage the tenant company profile, legal details, address, tax identifier, finance currency defaults, and the manual secondary-currency rate used across the current finance product."
        >
            <CompanySettingsForm />
        </SettingsPageFrame>
    );
}
