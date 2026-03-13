from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repo root so env file is found no matter where the process is started.
# This file is: SupaCRM/backend/app/core/config.py
# parents[0]=core, [1]=app, [2]=backend, [3]=SupaCRM (repo root)
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = (REPO_ROOT / ".env.supa").resolve()


class Settings(BaseSettings):
    # Load .env.supa from repo root
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=True,
        extra="ignore",
    )

    # ----------------------------
    # Environment / App
    # ----------------------------
    ENV: str = Field(default="dev", description="dev|staging|prod")
    APP_NAME: str = Field(default="SupaCRM API")
    DEBUG: bool = Field(default=False)

    APP_BASE_URL: str = Field(default="http://localhost:8000", description="Backend base URL")

    # Frontend URLs for email actions
    FRONTEND_BASE_URL: str = Field(default="http://localhost:5173")
    EMAIL_VERIFY_URL: str = Field(default="http://localhost:5173/verify-email")
    PASSWORD_RESET_URL: str = Field(default="http://localhost:5173/reset-password")

    # ----------------------------
    # Multi-tenancy
    # ----------------------------
    TENANT_HEADER_NAME: str = Field(default="X-Tenant-Id", description="Header used to identify tenant")
    REQUIRE_TENANT_HEADER: bool = Field(default=True, description="Enforce tenant header on tenant-scoped routes")

    # ----------------------------
    # Database / Cache
    # ----------------------------
    # Async runtime DB (application)
    DATABASE_URL_ASYNC: str = Field(..., description="Async Postgres DSN (asyncpg)")

    # Sync DB (Alembic migrations)
    DATABASE_URL_SYNC: str = Field(..., description="Sync Postgres DSN (psycopg) for Alembic")

    # Bootstrap/admin (Phase 2.2)
    DATABASE_URL_ADMIN_ASYNC: str = Field(
        ..., description="Admin async Postgres DSN (asyncpg) for tenant bootstrap"
    )
    DATABASE_URL_ADMIN_SYNC: str = Field(
        ..., description="Admin sync Postgres DSN (psycopg) for bootstrap scripts"
    )
    BOOTSTRAP_API_KEY: str = Field(..., description="API key to protect internal tenant bootstrap endpoint")

    # Legacy (deprecated). Keep for backward compatibility but do not use in new code.
    DATABASE_URL: str = Field(default="", description="Legacy DSN (deprecated)")

    # Redis (required for queues/workers)
    REDIS_URL: str = Field(..., description="Redis connection string")

    # ----------------------------
    # Auth / Security
    # ----------------------------
    JWT_SECRET: str = Field(..., description="Access token signing secret")
    REFRESH_TOKEN_SECRET: str = Field(..., description="Refresh token signing secret")
    PASSWORD_RESET_TOKEN_SECRET: str = Field(
        default="",
        description="Optional password reset token signing secret; falls back to JWT_SECRET when empty",
    )

    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ISSUER: str = Field(default="supacrm")
    JWT_AUDIENCE: str = Field(default="supacrm-api")
    ACCESS_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1, le=1440)
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30, ge=1, le=365)
    PASSWORD_RESET_TTL_MINUTES: int = Field(default=30, ge=5, le=240)
    AUTH_MAX_FAILED_ATTEMPTS: int = Field(default=5, ge=3, le=20)
    AUTH_LOCKOUT_MINUTES: int = Field(default=15, ge=1, le=1440)
    PASSWORD_MIN_LENGTH: int = Field(default=12, ge=8, le=128)

    # Trust X-Forwarded-* headers from reverse proxy (Nginx)
    TRUST_PROXY_HEADERS: bool = Field(default=True)

    # ----------------------------
    # Payments / Stripe
    # ----------------------------
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Payments redirect URLs (frontend)
    PAYMENTS_SUCCESS_URL: str = ""
    PAYMENTS_FAILURE_URL: str = ""

    # ----------------------------
    # Storage / MinIO
    # ----------------------------
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "supacrm"
    MINIO_USE_SSL: bool = False

    # ----------------------------
    # Email (SMTP)
    # ----------------------------
    SMTP_HOST: str = ""
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@supacrm.local"
    SMTP_USE_TLS: bool = False
    SMTP_USE_SSL: bool = False


settings = Settings()
