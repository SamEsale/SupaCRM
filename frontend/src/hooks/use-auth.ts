"use client";

import { useState } from "react";

import {
    getAuthStateFromStorage,
    getTenantId,
    setTenantId,
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
    const [authState] = useState<AuthState>(() => readAuthState() ?? initialAuthState);
    const isReady = true;

    return {
        ...authState,
        isReady,
    };
}
