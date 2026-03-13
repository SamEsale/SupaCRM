"""
Alembic environment configuration for SupaCRM.

This file is executed by Alembic when running migrations.

Key points:
- Uses the *sync* SQLAlchemy URL for migrations (psycopg/psycopg2), not asyncpg.
- Reads DATABASE_URL_SYNC from app.core.config.settings (which loads .env.supa).
- Uses app.db.Base.metadata as target_metadata so autogenerate can detect models.

IMPORTANT:
- Ensure your .env.supa exists at repo root and includes DATABASE_URL_SYNC.
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------
# Import app config + metadata
# ---------------------------------------------------------------------
import app.models  # noqa: F401  # ensures all tables are registered
from app.db import Base
from app.core.config import settings

# CRITICAL: ensure all models are imported so Base.metadata is populated.
# app/models.py should import every module that defines ORM models.


target_metadata = Base.metadata


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _get_sync_database_url() -> str:
    """
    Prefer DATABASE_URL_SYNC. Fall back to DATABASE_URL if needed.
    Must be a sync driver URL, e.g.:
      postgresql+psycopg://user:pass@host:5432/db
      postgresql+psycopg2://user:pass@host:5432/db
    """
    url = (getattr(settings, "DATABASE_URL_SYNC", "") or "").strip()
    if not url:
        url = (getattr(settings, "DATABASE_URL", "") or "").strip()

    if not url:
        url = (os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or "").strip()

    if not url:
        raise RuntimeError(
            "Missing DATABASE_URL_SYNC. Set it in .env.supa (recommended) "
            "or export DATABASE_URL_SYNC in the environment."
        )

    if "asyncpg" in url:
        raise RuntimeError(
            f"DATABASE_URL_SYNC must be a sync driver URL (psycopg/psycopg2), but got: {url}"
        )

    return url


def _set_sqlalchemy_url_on_config(url: str) -> None:
    config.set_main_option("sqlalchemy.url", url)


# ---------------------------------------------------------------------
# Autogenerate guardrails
# ---------------------------------------------------------------------
# These constraints already exist in DB and are handled by migrations.
# Some environments may cause Alembic to keep re-proposing them.
_CONSTRAINTS_TO_IGNORE = {
    "uq_role_permissions",
    "uq_tenant_user_roles",
    "uq_tenant_users_tenant_user",
}


def include_object(
    obj: Any,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: Any | None,
) -> bool:
    if type_ == "unique_constraint" and name in _CONSTRAINTS_TO_IGNORE:
        return False
    return True


# ---------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = _get_sync_database_url()
    _set_sqlalchemy_url_on_config(url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------
# Online migrations
# ---------------------------------------------------------------------
def run_migrations_online() -> None:
    url = _get_sync_database_url()
    _set_sqlalchemy_url_on_config(url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
