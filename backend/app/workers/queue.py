from __future__ import annotations

import logging
from typing import Any

from redis import Redis
from rq import Queue

from app.core.config import settings
from app.workers.tasks.auth_cache import invalidate_auth_cache, warm_auth_cache

logger = logging.getLogger("supacrm.worker.queue")


def get_redis_connection() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_queue() -> Queue:
    return Queue(settings.RQ_QUEUE_NAME, connection=get_redis_connection())


def enqueue_auth_cache_warmup(
    *,
    principal_snapshot: dict[str, Any] | None = None,
    profile_snapshot: dict[str, Any] | None = None,
) -> str | None:
    if not principal_snapshot and not profile_snapshot:
        return None

    try:
        job = get_queue().enqueue(
            warm_auth_cache,
            principal_snapshot=principal_snapshot,
            profile_snapshot=profile_snapshot,
            job_timeout=10,
        )
        return job.id
    except (
        Exception
    ):  # pragma: no cover - queue availability is optional in tests/local dev
        logger.warning("failed to enqueue auth cache warmup", exc_info=True)
        return None


def enqueue_auth_cache_invalidation(
    *,
    principal_access_jti: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> str | None:
    if not principal_access_jti and not (tenant_id and user_id):
        return None

    try:
        job = get_queue().enqueue(
            invalidate_auth_cache,
            principal_access_jti=principal_access_jti,
            tenant_id=tenant_id,
            user_id=user_id,
            job_timeout=10,
        )
        return job.id
    except (
        Exception
    ):  # pragma: no cover - queue availability is optional in tests/local dev
        logger.warning("failed to enqueue auth cache invalidation", exc_info=True)
        return None


def enqueue_marketing_campaign_execution(
    *,
    execution_id: str,
    tenant_id: str,
) -> str | None:
    """
    Thin launch-scope queue wrapper for marketing campaign execution.

    The worker task path is intentionally deferred until the dedicated
    marketing worker task is implemented. For now, queue availability
    remains optional and this function degrades safely in local/test
    environments by returning None if enqueue is unavailable or the task
    cannot be imported.
    """
    if not execution_id or not tenant_id:
        return None

    try:
        from app.workers.tasks.marketing import (
            execute_marketing_campaign,
        )  # local import on purpose

        job = get_queue().enqueue(
            execute_marketing_campaign,
            execution_id=execution_id,
            tenant_id=tenant_id,
            job_timeout=300,
        )
        return job.id
    except (
        Exception
    ):  # pragma: no cover - queue/task availability is optional in tests/local dev
        logger.warning("failed to enqueue marketing campaign execution", exc_info=True)
        return None
