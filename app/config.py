from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""

    environment: str = "dev"
    anthropic_api_key: str
    database_url: str = "sqlite+aiosqlite:///./chat.db"
    model_name: str = "claude-sonnet-4-5-20250929"
    llm_max_tokens: int = 16000
    thinking_enabled: bool = True
    thinking_budget_tokens: int = 10000

    # Default tenant/user for single-tenant POC
    default_tenant_id: str = "default"
    default_user_id: str = "default"

    # Auth (Now using JWT/Secret, so basic auth fields are optional or deprecated)
    auth_username: Optional[str] = "admin"
    auth_password: Optional[str] = "password"
    auth_secret_key: Optional[str] = "dev_secret_key_change_me_in_prod"

    # Development mode: bypass login when True
    dev_auth_bypass: bool = False

    # Proxy/IP handling
    trust_proxy_headers: bool = False
    trusted_proxy_ips: Optional[str] = None  # Comma-separated IPs/CIDRs for LB/proxy

    # Allow schema auto-create on startup (dev/local only)
    db_auto_create: bool = True

    # Invite guardrails
    invite_ip_allowlist: Optional[str] = None  # Comma-separated IPs/CIDRs
    invite_rate_limit_max: int = 10
    invite_rate_limit_window_seconds: int = 60

    # Skills configuration (prompt concatenation approach)
    skills_enabled: bool = False  # Set to True to include skill files in system prompt

    # Debug logging (LLM)
    debug_llm: bool = False

    # Feedback feature (only enable in staging/dev)
    feedback_enabled: bool = False

    # SMTP configuration for feedback emails
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: Optional[str] = None
    feedback_recipient_email: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra env vars (like POSTGRES_*) without validation error


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def validate_settings(settings: Settings) -> None:
    """Validate settings for non-dev environments."""
    env = settings.environment.lower().strip()
    if env in {"staging", "prod", "production"}:
        if not settings.database_url:
            raise ValueError("DATABASE_URL must be set for staging/production.")
        if settings.database_url.lower().startswith("sqlite"):
            raise ValueError("SQLite is not allowed for staging/production.")
        if not settings.auth_secret_key or settings.auth_secret_key == "dev_secret_key_change_me_in_prod":
            raise ValueError("AUTH_SECRET_KEY must be set to a non-default value for staging/production.")
        if settings.db_auto_create:
            raise ValueError("DB_AUTO_CREATE must be false for staging/production.")
