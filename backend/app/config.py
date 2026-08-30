"""Configuration management for GitScout backend using Pydantic Settings."""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GitScout / OSS Terminal"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./gitscout.db"

    # Security & CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://gitscout.dev",
        "https://*.vercel.app",
    ]
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # GitHub Scraper & Scheduler
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_API_BASE: str = "https://api.github.com"
    SCRAPE_INTERVAL_MINUTES: int = 30
    DEFAULT_REPO_LIMIT: int = 20
    ENABLE_BACKGROUND_CRAWLER: bool = False

    # Multi-Channel Dispatchers
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    DISCORD_WEBHOOK_URL: Optional[str] = None

    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "alerts@gitscout.dev"

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "alerts@gitscout.dev"

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # Billing & Monetization
    DODO_PAYMENTS_API_KEY: Optional[str] = None
    DODO_PAYMENTS_WEBHOOK_KEY: Optional[str] = None
    DODO_ENVIRONMENT: str = "test_mode"

    LEMON_SQUEEZY_API_KEY: Optional[str] = None
    LEMON_SQUEEZY_STORE_ID: Optional[str] = None
    LEMON_SQUEEZY_WEBHOOK_SECRET: Optional[str] = None

    FRONTEND_URL: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()
