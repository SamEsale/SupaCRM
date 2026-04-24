"use client";

import { useEffect, useState } from "react";

import {
    getAuthStateFromStorage,
    getTenantId,
    setTenantId,
    subscribeAuthStorage,
} from "@/lib/auth-storage";
import type { AuthState } from "@/types/auth";

interface UseAuthResult extends AuthState {
    isReady: boolean;
}

const initialAuthState: AuthState = {
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
};

function readAuthState(): AuthState {
    const nextState = getAuthStateFromStorage();

    if (nextState.user?.tenant_id && !getTenantId()) {
        setTenantId(nextState.user.tenant_id);
    }

    return nextState;
}

export function useAuth(): UseAuthResult {
    const [authState, setAuthState] = useState<AuthState>(initialAuthState);
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        function syncAuthState(): void {
            setAuthState(readAuthState());
            setIsReady(true);
        }

        syncAuthState();

        return subscribeAuthStorage(syncAuthState);
    }, []);

    return {
        ...authState,
        isReady,
    };
}
