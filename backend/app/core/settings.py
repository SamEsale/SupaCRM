from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Existing app/user DB URL (already in your project)
    DATABASE_URL: str

    # NEW: Admin DB URL (table-owner / bypass-RLS role)
    # Example: postgresql+asyncpg://postgres:pass@localhost:5432/supacrm
    DATABASE_URL_ADMIN: str

    # NEW: one-time bootstrap auth key (protects internal endpoint)
    BOOTSTRAP_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
