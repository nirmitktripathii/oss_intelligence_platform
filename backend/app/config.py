"""Configuration management for GitScout backend using Pydantic Settings."""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
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

    # Upstash Serverless Redis Cache
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # GitHub Scraper & Scheduler
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_API_BASE: str = "https://api.github.com"
    SCRAPE_INTERVAL_MINUTES: int = 30
    DEFAULT_REPO_LIMIT: int = 20
    ENABLE_BACKGROUND_CRAWLER: bool = False

    # ── AI Semantic Triage (LLM enhancement layer) ──
    # Every field is optional. When no provider key is set the triage engine
    # degrades to deterministic AST-only output — it never fabricates an AI result.
    # Providers are free-tier friendly: Google Gemini / Gemma, Groq (Llama 3.3),
    # any OpenAI-compatible endpoint, or a local Ollama for development only.
    LLM_TRIAGE_ENABLED: bool = True          # master switch; False => always AST-only
    LLM_PROVIDER: Optional[str] = None       # force one of: gemini|groq|openai|ollama (else auto)
    LLM_MODEL: Optional[str] = None          # override the per-provider default model id
    LLM_TIMEOUT_SECONDS: float = 20.0
    LLM_CACHE_TTL_SECONDS: int = 604800      # persist an enrichment for 7 days in Redis

    GEMINI_API_KEY: Optional[str] = None     # Google AI Studio free tier (gemini-2.0-flash, gemma-2-27b-it, …)
    GROQ_API_KEY: Optional[str] = None        # Groq free tier (llama-3.3-70b-versatile, …)
    OPENAI_API_KEY: Optional[str] = None      # OpenAI or any compatible endpoint
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: Optional[str] = None     # e.g. http://localhost:11434 — local dev only, never on Render

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
