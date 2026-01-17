from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""

    environment: str = "dev"
    anthropic_api_key: str
    database_url: str = "postgresql+asyncpg://dungeon:password@localhost:5432/dungeon"
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

    # Auth/session TTLs (BFF migration)
    invite_ttl_hours: int = 24
    account_ttl_days: int = 7
    session_idle_timeout_minutes: int = 240
    session_absolute_ttl_days: Optional[int] = None

    # Session cookie settings
    session_cookie_name: str = "session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "Lax"
    session_cookie_domain: Optional[str] = None

    # Invite guardrails
    allow_indefinite_invites: bool = False
    default_account_expires: bool = True

    # Turnstile captcha
    turnstile_site_key: Optional[str] = None
    turnstile_secret_key: Optional[str] = None

    # Postmark email delivery
    postmark_server_token: Optional[str] = None
    postmark_from_email: Optional[str] = None
    postmark_message_stream: str = "outbound"
    invite_email_send_mode: str = "manual"  # auto or manual
    public_app_url: Optional[str] = None

    # Proxy/IP handling
    trust_proxy_headers: bool = False
    trusted_proxy_ips: Optional[str] = None  # Comma-separated IPs/CIDRs for LB/proxy
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]

    # Allow schema auto-create on startup (dev/local only)
    db_auto_create: bool = True

    # Invite guardrails
    invite_ip_allowlist: Optional[str] = None  # Comma-separated IPs/CIDRs
    invite_rate_limit_max: int = 10
    invite_rate_limit_window_seconds: int = 60

    # Auth rate limits
    login_rate_limit_max: int = 10
    login_rate_limit_window_seconds: int = 60
    register_rate_limit_max: int = 10
    register_rate_limit_window_seconds: int = 60
    invite_request_rate_limit_max: int = 5
    invite_request_rate_limit_window_seconds: int = 300

    # Skills configuration (deprecated: compiled skills are always included when present)
    skills_enabled: bool = True

    # Debug logging (LLM)
    debug_llm: bool = False

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",  # Allow extra env vars (like POSTGRES_*) without validation error
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def validate_settings(settings: Settings) -> None:
    """Validate settings for non-dev environments."""
    env = settings.environment.lower().strip()
    if settings.database_url.lower().startswith("sqlite"):
        raise ValueError("SQLite is no longer supported. Use Postgres (DATABASE_URL).")
    if env in {"staging", "prod", "production"}:
        if not settings.database_url:
            raise ValueError("DATABASE_URL must be set for staging/production.")
        if not settings.auth_secret_key or settings.auth_secret_key == "dev_secret_key_change_me_in_prod":
            raise ValueError("AUTH_SECRET_KEY must be set to a non-default value for staging/production.")
        if settings.db_auto_create:
            raise ValueError("DB_AUTO_CREATE must be false for staging/production.")
        if not settings.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true for staging/production.")
        if not settings.turnstile_site_key or not settings.turnstile_secret_key:
            raise ValueError("Turnstile keys must be set for staging/production.")
        if settings.invite_email_send_mode not in {"auto", "manual"}:
            raise ValueError("INVITE_EMAIL_SEND_MODE must be 'auto' or 'manual'.")
        if settings.invite_email_send_mode == "auto":
            if not settings.postmark_server_token or not settings.postmark_from_email:
                raise ValueError("Postmark settings must be set when invite email send mode is auto.")
            if not settings.public_app_url:
                raise ValueError("PUBLIC_APP_URL must be set when invite email send mode is auto.")
