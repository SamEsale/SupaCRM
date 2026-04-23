from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.security.auth_cache import auth_cache

logger = logging.getLogger("supacrm.worker")


async def _warm_auth_cache_async(
    *,
    principal_snapshot: dict[str, Any] | None = None,
    profile_snapshot: dict[str, Any] | None = None,
) -> None:
    if principal_snapshot:
        access_token_jti = str(principal_snapshot["access_token_jti"])
        ttl_seconds = int(principal_snapshot["principal_ttl_seconds"])
        await auth_cache.set_principal_snapshot(
            access_token_jti,
            principal_snapshot["snapshot"],
            ttl_seconds=ttl_seconds,
        )

    if profile_snapshot:
        tenant_id = str(profile_snapshot["tenant_id"])
        user_id = str(profile_snapshot["user_id"])
        ttl_seconds = int(profile_snapshot["profile_ttl_seconds"])
        await auth_cache.set_profile_snapshot(
            tenant_id,
            user_id,
            profile_snapshot["snapshot"],
            ttl_seconds=ttl_seconds,
        )


async def _invalidate_auth_cache_async(
    *,
    principal_access_jti: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> None:
    if principal_access_jti:
        await auth_cache.invalidate_principal_snapshot(principal_access_jti)

    if tenant_id and user_id:
        await auth_cache.invalidate_profile_snapshot(tenant_id, user_id)


def warm_auth_cache(
    *,
    principal_snapshot: dict[str, Any] | None = None,
    profile_snapshot: dict[str, Any] | None = None,
) -> None:
    asyncio.run(
        _warm_auth_cache_async(
            principal_snapshot=principal_snapshot,
            profile_snapshot=profile_snapshot,
        )
    )


def invalidate_auth_cache(
    *,
    principal_access_jti: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> None:
    asyncio.run(
        _invalidate_auth_cache_async(
            principal_access_jti=principal_access_jti,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    )
