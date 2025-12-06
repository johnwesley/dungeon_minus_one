from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""

    anthropic_api_key: str
    database_url: str = "sqlite+aiosqlite:///./chat.db"
    model_name: str = "claude-opus-4-5-20251101"

    # Default tenant/user for single-tenant POC
    default_tenant_id: str = "default"
    default_user_id: str = "default"

    # Auth (Now using JWT/Secret, so basic auth fields are optional or deprecated)
    auth_username: Optional[str] = "admin"
    auth_password: Optional[str] = "password"
    auth_secret_key: Optional[str] = "dev_secret_key_change_me_in_prod"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
