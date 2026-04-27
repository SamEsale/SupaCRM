import SettingsPageFrame from "@/components/settings/SettingsPageFrame";
import SecuritySettingsPage from "@/components/settings/SecuritySettingsPage";

export default function SecuritySettingsRoute() {
    return (
        <SettingsPageFrame
            title="Security"
            description="Review account security, tenant access posture, RBAC visibility, and supported recovery actions using the existing auth and tenancy foundations."
        >
            <SecuritySettingsPage />
        </SettingsPageFrame>
    );
}
