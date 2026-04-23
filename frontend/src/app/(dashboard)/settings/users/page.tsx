import SettingsPageFrame from "@/components/settings/SettingsPageFrame";
import UsersSettingsPage from "@/components/settings/UsersSettingsPage";

export default function UsersSettingsRoute() {
    return (
        <SettingsPageFrame
            title="Users & Roles"
            description="Review tenant users, current role assignments, active membership state, and safe access updates without depending on onboarding workflows."
        >
            <UsersSettingsPage />
        </SettingsPageFrame>
    );
}
