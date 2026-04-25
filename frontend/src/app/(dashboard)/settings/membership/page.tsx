import SettingsPageFrame from "@/components/settings/SettingsPageFrame";
import MembershipSettingsPage from "@/components/settings/MembershipSettingsPage";

export default function MembershipSettingsRoute() {
    return (
        <SettingsPageFrame
            title="Membership"
            description="Manage tenant access state, ownership lifecycle, and safe membership removal without leaving the tenant without administrative coverage."
        >
            <MembershipSettingsPage />
        </SettingsPageFrame>
    );
}
