"use client";

import { useEffect, useState } from "react";

import {
    getAuthStateFromStorage,
    getTenantId,
    subscribeAuthStorage,
    setTenantId,
} from "@/lib/auth-storage";
import type { AuthState } from "@/types/auth";

interface UseAuthResult extends AuthState {
    isReady: boolean;
}

function readAuthState(): AuthState {
    const nextState = getAuthStateFromStorage();

    if (nextState.user?.tenant_id && !getTenantId()) {
        setTenantId(nextState.user.tenant_id);
    }

    return nextState;
}

export function useAuth(): UseAuthResult {
    const [authState, setAuthState] = useState<AuthState>(() => readAuthState());
    const isReady = true;

    useEffect(() => {
        function syncAuthState(): void {
            setAuthState(readAuthState());
        }

        syncAuthState();

        const unsubscribe = subscribeAuthStorage(syncAuthState);

        return () => {
            unsubscribe();
        };
    }, []);

    return {
        ...authState,
        isReady,
    };
}
