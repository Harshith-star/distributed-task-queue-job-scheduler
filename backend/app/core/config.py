"""
app/core/config.py

Central configuration via Pydantic Settings.

Why Pydantic Settings instead of os.getenv()?
  - Type coercion: "30" → int automatically.
  - Validation: fails at startup with a clear error, not mid-request.
  - IDE auto-complete and type safety across the codebase.
  - Single source of truth — no scattered os.getenv() calls.
"""
import sys
from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables.

    All fields without a default value are REQUIRED.
    The application calls get_settings() at startup; missing required fields
    raise a ValidationError and the process exits with a clear message.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unknown env vars (e.g. Docker injected vars)
    )

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "TaskQ"
    APP_ENV: Literal["development", "production"] = "production"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://frontend:80"

    # ── Database (required) ──────────────────────────────────────────
    DATABASE_URL: str  # no default → required

    # ── Security (required) ──────────────────────────────────────────
    SECRET_KEY: str    # no default → required
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis / Celery ───────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Email ────────────────────────────────────────────────────────
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@taskq.io"

    # ── Celery tuning ────────────────────────────────────────────────
    CELERY_MAX_RETRIES: int = 3
    CELERY_RETRY_BACKOFF: int = 60   # seconds; doubles on each retry
    CELERY_TASK_TIMEOUT: int = 300   # seconds per task

    # ── Rate limiting (requests per minute per user) ─────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Dashboard cache TTL ──────────────────────────────────────────
    DASHBOARD_CACHE_TTL: int = 30    # seconds

   

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        """Fail fast with a helpful message if secrets are placeholder values."""
        placeholder_fragments = {"REPLACE", "your-", "change-me", "todo"}
        for field_name in ("SECRET_KEY", "DATABASE_URL"):
            val = getattr(self, field_name, "")
            if any(p in val for p in placeholder_fragments):
                print(
                    f"\n[FATAL] {field_name} still contains a placeholder value. "
                    "Copy .env.example → .env and set real values.\n",
                    file=sys.stderr,
                )
                sys.exit(1)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance.

    lru_cache(maxsize=1) ensures Settings() is instantiated once at startup.
    In tests, call get_settings.cache_clear() before overriding.
    """
    return Settings()


# Module-level convenience alias used in import-time code (e.g. Celery config).
settings: Settings = get_settings()
