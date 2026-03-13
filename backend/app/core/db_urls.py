import os
from app.core.env import load_env_supa

def get_sync_dsn_psycopg() -> str:
    load_env_supa()
    dsn = os.getenv("DATABASE_URL_SYNC")
    if not dsn:
        raise RuntimeError("DATABASE_URL_SYNC is not set")

    # psycopg expects postgresql:// (not SQLAlchemy-style)
    if dsn.startswith("postgresql+psycopg://"):
        dsn = "postgresql://" + dsn[len("postgresql+psycopg://"):]

    return dsn


def get_async_dsn_sqlalchemy() -> str:
    load_env_supa()
    dsn = os.getenv("DATABASE_URL_ASYNC")
    if not dsn:
        raise RuntimeError("DATABASE_URL_ASYNC is not set")
    return dsn
