from __future__ import annotations

import asyncio
import logging

from app.db import async_session_factory, set_tenant_guc
from app.marketing.service import (
    fail_marketing_campaign_execution,
    process_email_campaign_execution,
)

logger = logging.getLogger("supacrm.worker")


async def _execute_marketing_campaign_async(
    *,
    execution_id: str,
    tenant_id: str,
) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await set_tenant_guc(session, tenant_id)
            await process_email_campaign_execution(session, execution_id=execution_id)


async def _mark_execution_failed_async(
    *,
    execution_id: str,
    tenant_id: str,
    failure_reason: str,
) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await set_tenant_guc(session, tenant_id)
            await fail_marketing_campaign_execution(
                session,
                execution_id=execution_id,
                failure_reason=failure_reason,
            )


def execute_marketing_campaign(*, execution_id: str, tenant_id: str) -> None:
    try:
        asyncio.run(
            _execute_marketing_campaign_async(
                execution_id=execution_id,
                tenant_id=tenant_id,
            )
        )
    except Exception as exc:
        logger.exception(
            "marketing campaign execution worker failed",
            extra={"execution_id": execution_id, "tenant_id": tenant_id},
        )
        asyncio.run(
            _mark_execution_failed_async(
                execution_id=execution_id,
                tenant_id=tenant_id,
                failure_reason=f"Worker execution failed: {exc}",
            )
        )
        raise
