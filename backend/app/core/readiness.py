from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from redis.asyncio import Redis
from sqlalchemy import text
from minio import Minio

from app.core.config import settings
from app.db import async_engine
from app.db_admin import admin_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


@lru_cache(maxsize=1)
def get_alembic_heads() -> tuple[str, ...]:
    """Return the current Alembic head revision(s) for release-state verification."""

    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)
    return tuple(script.get_heads())


def _validate_security_settings() -> None:
    required_strings = {
        "DATABASE_URL_ASYNC": settings.DATABASE_URL_ASYNC,
        "DATABASE_URL_SYNC": settings.DATABASE_URL_SYNC,
        "DATABASE_URL_ADMIN_ASYNC": settings.DATABASE_URL_ADMIN_ASYNC,
        "DATABASE_URL_ADMIN_SYNC": settings.DATABASE_URL_ADMIN_SYNC,
        "REDIS_URL": settings.REDIS_URL,
        "JWT_SECRET": settings.JWT_SECRET,
        "REFRESH_TOKEN_SECRET": settings.REFRESH_TOKEN_SECRET,
        "BOOTSTRAP_API_KEY": settings.BOOTSTRAP_API_KEY,
        "JWT_ALGORITHM": settings.JWT_ALGORITHM,
        "JWT_ISSUER": settings.JWT_ISSUER,
        "JWT_AUDIENCE": settings.JWT_AUDIENCE,
    }
    missing = [name for name, value in required_strings.items() if not str(value).strip()]
    if missing:
        raise RuntimeError(f"missing required security settings: {', '.join(sorted(missing))}")

    if settings.ACCESS_TOKEN_TTL_MINUTES > 15:
        raise RuntimeError("ACCESS_TOKEN_TTL_MINUTES must not exceed 15 minutes")


async def check_database_ready() -> None:
    _validate_security_settings()

    async with asyncio.timeout(1.5):
        async with async_engine.connect() as connection:
            await connection.execute(text("select 1"))

    async with asyncio.timeout(1.5):
        async with admin_engine.connect() as connection:
            result = await connection.execute(text("select version_num from alembic_version limit 1"))
            version = result.scalar_one_or_none()
            if not version:
                raise RuntimeError("alembic_version row missing")

            if version not in get_alembic_heads():
                expected = ", ".join(get_alembic_heads()) or "<none>"
                raise RuntimeError(f"database revision {version} is not at head ({expected})")


async def check_redis_ready() -> None:
    async with asyncio.timeout(1.5):
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.ping()

            if not settings.RQ_HEALTHCHECK_ENABLED:
                return

            queue_key = f"rq:queue:{settings.RQ_QUEUE_NAME}"
            if not await client.exists(queue_key):
                raise RuntimeError(f"RQ queue missing: {settings.RQ_QUEUE_NAME}")
        finally:
            await client.aclose()


def _build_storage_client() -> Minio:
    endpoint = settings.MINIO_ENDPOINT.strip()
    if not endpoint:
        raise RuntimeError("MINIO_ENDPOINT is not configured")

    access_key = (settings.MINIO_ACCESS_KEY or settings.MINIO_ROOT_USER).strip()
    secret_key = (settings.MINIO_SECRET_KEY or settings.MINIO_ROOT_PASSWORD).strip()
    if not access_key or not secret_key:
        raise RuntimeError("MinIO credentials are not configured")

    normalized_endpoint = endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        normalized_endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=bool(settings.MINIO_USE_SSL or endpoint.startswith("https://")),
    )


def storage_readiness_required() -> bool:
    return bool(settings.MINIO_ENDPOINT.strip())


async def check_storage_ready() -> None:
    if not storage_readiness_required():
        return

    async with asyncio.timeout(1.5):
        await asyncio.to_thread(_check_storage_ready_sync)


def _check_storage_ready_sync() -> None:
    client = _build_storage_client()
    client.list_buckets()
