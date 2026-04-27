"""
Database configuration and session management for SupaCRM.

Provides:
- Async SQLAlchemy engine for PostgreSQL (asyncpg)
- Async session factory
- Base declarative model for all entities
- FastAPI dependency (get_db)
- Multi-tenant RLS support via PostgreSQL GUC: app.tenant_id
- Connection pooling and lifecycle management

IMPORTANT NOTES:
- Do NOT define a module-level variable named `metadata` when using SQLAlchemy Declarative.
  Declarative models already use `Base.metadata`.

RLS / tenant scoping (recommended approach):
- We set tenant context using:
    SELECT set_config('app.tenant_id', :tenant_id, true)
  The 3rd arg `true` means transaction-scoped ("LOCAL").
- Because it's LOCAL, it only applies within the current transaction.
  Therefore, `get_db()` opens a transaction, sets the tenant, then yields the session.
  The transaction is committed when the request finishes (or rolled back on error).

RULE:
- Prefer not calling `session.commit()` inside route handlers.
  Use `session.flush()` if you need the row persisted before returning.
  (If you do commit inside routes, you'll end the transaction and the LOCAL GUC will be cleared.)
"""

from __future__ import annotations

import asyncio
import contextvars
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import Request
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, DateTime, String, func, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# =============================================================================
# Base Model for all ORM entities
# =============================================================================
Base = declarative_base()

# =============================================================================
# Tenant context (request/task local via contextvars)
# =============================================================================
_current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_tenant_id",
    default=None,
)


def set_current_tenant_id(tenant_id: Optional[str]):
    """
    Store the tenant id in a context var (request/task local).
    Returns a token that can be used to reset() later.
    """
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token) -> None:
    """Reset the context var using the token returned by set_current_tenant_id()."""
    _current_tenant_id.reset(token)


def get_current_tenant_id() -> Optional[str]:
    """Read the tenant id from the context var (request/task local)."""
    return _current_tenant_id.get()


# =============================================================================
# Async Engine Configuration
# =============================================================================
def create_db_engine() -> AsyncEngine:
    """
    Create and configure an async SQLAlchemy engine for PostgreSQL.
    """
    if not settings.DATABASE_URL_ASYNC:
        raise RuntimeError("DATABASE_URL_ASYNC is not set")

    return create_async_engine(
        settings.DATABASE_URL_ASYNC,
        echo=settings.DEBUG,  # useful in dev, disable in prod
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
        },
    )


async_engine: AsyncEngine = create_db_engine()

async_session_factory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    future=True,
)

# =============================================================================
# Multi-Tenant RLS Helpers
# =============================================================================
async def set_tenant_guc(session: AsyncSession, tenant_id: str) -> None:
    """
    Set the tenant context for RLS using a PostgreSQL custom GUC.

    Uses set_config() because SET ... with bind params results in:
      syntax error at or near "$1"
    under asyncpg prepared statements.

    NOTE: is_local=true makes it transaction-scoped (recommended).
    """
    if not tenant_id:
        return

    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )


async def reset_tenant_guc(session: AsyncSession) -> None:
    """
    Defensive reset. Safe even if not set.
    Use inside the request transaction to avoid state bleeding if code changes later.
    """
    await session.execute(text("RESET app.tenant_id"))


# =============================================================================
# Dependency Injection for FastAPI
# =============================================================================
async def get_db(
    request: Request,
    tenant_id: Optional[str] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession inside a single request-scoped transaction.

    Tenant selection order:
    1) Explicit tenant_id passed into dependency (rare)
    2) request.state.tenant_id (set by TenantMiddleware)
    3) Tenant id in context var (set by TenantMiddleware)
    4) None (public/system endpoints)

    Because we use set_config(..., true), we MUST keep the transaction open while
    the request runs so tenant context applies to all statements.
    """
    state_tenant_id = getattr(request.state, "tenant_id", None)
    effective_tenant_id = tenant_id or state_tenant_id or get_current_tenant_id()

    async with async_session_factory() as session:
        # Open ONE transaction for the whole request.
        # This ensures set_config(..., true) applies to every statement.
        async with session.begin():
            if effective_tenant_id:
                await set_tenant_guc(session, effective_tenant_id)
            else:
                await reset_tenant_guc(session)

            # Yield session to route handler; commit happens when we exit session.begin()
            yield session

        # Session closes automatically when exiting the outer context manager.


# =============================================================================
# Database Lifecycle Management
# =============================================================================
async def init_db() -> None:
    """
    DEV convenience: create tables.

    In production, use Alembic migrations instead of create_all().
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def run_database_migrations() -> None:
    """
    Apply Alembic migrations in non-production environments.

    This keeps local development databases aligned with the current schema
    without weakening production deployment discipline.
    """

    def _upgrade() -> None:
        backend_root = Path(__file__).resolve().parents[1]
        alembic_ini = backend_root / "alembic.ini"
        config = Config(str(alembic_ini))
        command.upgrade(config, "head")

    await asyncio.to_thread(_upgrade)


async def close_db() -> None:
    """Close all database connections."""
    await async_engine.dispose()


# =============================================================================
# Base Mixins
# =============================================================================
class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        server_default=func.now(),
    )


class TenantMixin:
    """Mixin to add tenant_id for multi-tenant isolation."""

    tenant_id = Column(
        String(64),
        nullable=False,
        index=True,
    )
