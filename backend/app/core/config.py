import os
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repo root so env file is found no matter where the process is started.
# This file is: SupaCRM/backend/app/core/config.py
# parents[0]=core, [1]=app, [2]=backend, [3]=SupaCRM (repo root)
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = (REPO_ROOT / ".env.supa").resolve()
SECRET_FILE_FIELDS = (
    "DATABASE_URL_ASYNC",
    "DATABASE_URL_SYNC",
    "DATABASE_URL_ADMIN_ASYNC",
    "DATABASE_URL_ADMIN_SYNC",
    "REDIS_URL",
    "JWT_SECRET",
    "REFRESH_TOKEN_SECRET",
    "PASSWORD_RESET_TOKEN_SECRET",
    "BOOTSTRAP_API_KEY",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "STRIPE_API_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "SMTP_USER",
    "SMTP_PASSWORD",
)


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
    LOG_LEVEL: str = Field(default="INFO", description="Application log level")

    # Frontend URLs for email actions
    FRONTEND_BASE_URL: str = Field(default="http://localhost:3000")
    EMAIL_VERIFY_URL: str = Field(default="http://localhost:3000/verify-email")
    PASSWORD_RESET_URL: str = Field(default="http://localhost:3000/reset-password")

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
    RQ_HEALTHCHECK_ENABLED: bool = Field(
        default=False,
        description="Enable optional RQ queue health checks in readiness",
    )
    RQ_QUEUE_NAME: str = Field(default="default", description="Primary RQ queue name for readiness checks")

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
    ACCESS_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1, le=15)
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
    MINIO_ROOT_USER: str = ""
    MINIO_ROOT_PASSWORD: str = ""
    S3_BUCKET: str = ""

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

    @model_validator(mode="before")
    @classmethod
    def _load_file_backed_secrets(cls, values):
        if not isinstance(values, dict):
            return values

        resolved = dict(values)
        for field_name in SECRET_FILE_FIELDS:
            if cls._looks_real(resolved.get(field_name)):
                continue

            file_env_name = f"{field_name}_FILE"
            file_path = resolved.get(file_env_name) or os.getenv(file_env_name)
            if not file_path:
                continue

            path = Path(str(file_path)).expanduser()
            if not path.exists():
                raise ValueError(f"{file_env_name} points to missing file: {path}")

            file_value = path.read_text(encoding="utf-8").strip()
            if not cls._looks_real(file_value):
                raise ValueError(f"{file_env_name} file is empty or invalid: {path}")
            resolved[field_name] = file_value

        return resolved

    @field_validator(
        "DATABASE_URL_ASYNC",
        "DATABASE_URL_SYNC",
        "DATABASE_URL_ADMIN_ASYNC",
        "DATABASE_URL_ADMIN_SYNC",
        "REDIS_URL",
        "JWT_SECRET",
        "REFRESH_TOKEN_SECRET",
        "BOOTSTRAP_API_KEY",
        mode="before",
    )
    @classmethod
    def _require_non_empty(cls, value: str, info):
        normalized = value if isinstance(value, str) else str(value or "")
        normalized = normalized.strip()
        if not cls._looks_real(normalized):
            raise ValueError(f"{info.field_name} must be configured with a real value")
        return normalized

    @staticmethod
    def _looks_real(value: object) -> bool:
        if value is None:
            return False
        if not isinstance(value, str):
            value = str(value)
        normalized = value.strip()
        if not normalized:
            return False
        if normalized.startswith("REPLACE_WITH_REAL_"):
            return False
        return True


settings = Settings()
