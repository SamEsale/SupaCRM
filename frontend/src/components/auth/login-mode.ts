const LOCAL_LOGIN_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export function isLocalLoginHost(hostname: string | undefined): boolean {
    if (!hostname) {
        return false;
    }

    const normalizedHost = hostname.trim().toLowerCase();
    if (normalizedHost === "::1") {
        return true;
    }

    const hostWithoutPort = normalizedHost.startsWith("[")
        ? normalizedHost.slice(1, normalizedHost.indexOf("]") > 0 ? normalizedHost.indexOf("]") : undefined)
        : normalizedHost.split(":")[0];

    return LOCAL_LOGIN_HOSTS.has(hostWithoutPort);
}
