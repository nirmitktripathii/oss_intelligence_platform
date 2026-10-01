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
    # Providers are free-tier friendly: Google Gemini / Gemma, Groq, any
    # OpenAI-compatible endpoint, or a local Ollama for development only.
    LLM_TRIAGE_ENABLED: bool = True          # master switch; False => always AST-only
    LLM_PROVIDER: Optional[str] = None       # force one of: bedrock|gemini|groq|openai|ollama (else auto)
    LLM_MODEL: Optional[str] = None          # override the per-provider default model id
    LLM_TIMEOUT_SECONDS: float = 30.0        # interactive triage synthesis call budget
    LLM_CACHE_TTL_SECONDS: int = 604800      # persist an enrichment for 7 days in Redis
    # After a provider raises, skip it for this long (when another provider is available) so a
    # broken one (expired key, zero quota) costs one slow call per window, not one per request.
    LLM_PROVIDER_COOLDOWN_SECONDS: float = 120.0

    # Long issue descriptions: bodies up to this many characters are fed to the AI
    # verbatim. A longer body is condensed ONCE at index time by a single fast
    # flash-lite call into a <LLM_BODY_MAX_CHARS summary that preserves every point
    # (guidelines, procedures, rules, constraints, repro steps) and is stored+indexed
    # in Neon (Issue.body_summary). Deterministic AST/repro always use the FULL raw
    # body; only the LLM synthesis layer consumes the summary. If no provider key is
    # set the read path degrades honestly to a hard body[:LLM_BODY_MAX_CHARS] slice.
    LLM_BODY_MAX_CHARS: int = 8000
    # The summarization call runs in the background scraper (not a user request), so it
    # gets a lenient timeout independent of the interactive path.
    LLM_SUMMARY_TIMEOUT_SECONDS: float = 60.0

    # Google AI Studio free tier — all reachable via the same Gemini API. Defaults to
    # gemini-3.5-flash-lite; set LLM_MODEL to pick another. Free rate limits (RPM/TPM/RPD):
    #   gemini-3.5-flash-lite  15 / 250,000 / 500
    #   gemini-3.1-flash-lite  15 / 250,000 / 500
    #   gemma-4-26b-a4b-it     30 /  16,000 / 14,400   (MoE)
    #   gemma-4-31b-it         30 /  16,000 / 14,400
    GEMINI_API_KEY: Optional[str] = None
    # Groq free tier — Llama 3.3 is NOT offered here; default is openai/gpt-oss-120b
    # (30 RPM / 8,000 TPM / 200,000 TPD). Other free chat models: openai/gpt-oss-20b,
    # openai/gpt-oss-safeguard-20b, qwen/qwen3.8-27b, qwen/qwen3.6-27b, groq/compound[-mini].
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None      # OpenAI or any compatible endpoint
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: Optional[str] = None     # e.g. http://localhost:11434 — local dev only, never on Render

    # Amazon Bedrock (AWS-native provider, Converse API). Enabled by EITHER credential:
    #   - AWS_BEARER_TOKEN_BEDROCK: a Bedrock API key (deploys, e.g. Render). boto3 reads it
    #     straight from the environment — the app never passes the key around itself.
    #   - BEDROCK_AWS_PROFILE: a named AWS CLI profile (local dev, e.g. after `aws login`).
    # Model ids are account/region specific: list them with
    #   aws bedrock list-inference-profiles --region us-east-1
    # BEDROCK_MODEL_ID is Bedrock's own override; the shared LLM_MODEL is deliberately NOT
    # applied here, because a Gemini/Groq model id set for the fallbacks is invalid on Bedrock.
    AWS_BEARER_TOKEN_BEDROCK: Optional[str] = None
    BEDROCK_AWS_PROFILE: Optional[str] = None
    BEDROCK_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: Optional[str] = None     # default: us.amazon.nova-2-lite-v1:0
    # Always sent explicitly: an unset maxTokens makes Bedrock reserve the model's full output
    # quota per call, which surfaces as spurious ThrottlingException under load.
    BEDROCK_MAX_TOKENS: int = 4096

    # Real-code grounding: fetch the localized file's actual source (GitHub Contents API,
    # reuses GITHUB_TOKEN) and feed it to the LLM so diagnoses are grounded, not guessed.
    LLM_GROUND_IN_SOURCE: bool = True
    LLM_GROUND_MAX_FILES: int = 2             # how many top localized files to fetch
    LLM_SOURCE_MAX_CHARS: int = 6000          # total injected source budget (bounds prompt size)
    GITHUB_FILE_CACHE_TTL_SECONDS: int = 86400

    # Grounded enrichment layers, each independently switchable (all reuse the fetched source
    # and ride the same free-tier chain). False => that card falls back to its deterministic
    # AST scaffold / template rather than an LLM answer.
    LLM_SYNTH_REPRO: bool = True              # grounded reproduction script (real symbols)
    LLM_SYNTH_PATCH: bool = True              # grounded unified-diff patch + regression risk
    LLM_CONTRIBUTING: bool = True             # summarize the repo's REAL CONTRIBUTING guide
    LLM_CONTRIBUTING_MAX_CHARS: int = 6000    # bound the guide text fed to the summarizer
    CONTRIBUTING_CACHE_TTL_SECONDS: int = 604800  # cache a repo's CONTRIBUTING guide for 7 days

    # ── Agent planner (Developer Mission Control) ──
    # The planner reasons through the LLM chain above and acts only through MCP servers.
    # Unset => the /agent endpoints answer 503 and nothing else changes. JSON list, e.g.
    #   [{"name": "gitscout", "url": "http://127.0.0.1:9000/mcp",
    #     "auto_approve": ["search_issues", "get_issue", "analyze_issue"]}]
    # A tool NOT listed in its server's auto_approve pauses for the user's confirmation,
    # so list only read-only tools there.
    AGENT_MCP_SERVERS: Optional[str] = None
    AGENT_MAX_STEPS: int = 6                  # tool calls per mission before it must answer
    AGENT_TOOL_TIMEOUT_SECONDS: float = 90.0  # per MCP call; triage tools may invoke an LLM
    AGENT_MISSION_TTL_SECONDS: int = 86400    # how long a mission (and its session) is kept
    AGENT_RATE_LIMIT: str = "10/minute"       # per client, on starting and approving missions

    # Sign-in for tools that change things (Git/CI, email). Anyone may use the read-only tools.
    # Create a GitHub OAuth App whose callback URL is AUTH_GITHUB_CALLBACK_URL
    # (https://<api host>/api/v1/auth/github/callback), then set these. AUTH_SECRET signs the
    # session tokens: use 32+ random characters. Only logins in AUTH_ALLOWED_LOGINS (comma
    # separated) may approve a write; empty means nobody can.
    AUTH_SECRET: Optional[str] = None
    AUTH_GITHUB_CLIENT_ID: Optional[str] = None
    AUTH_GITHUB_CLIENT_SECRET: Optional[str] = None
    AUTH_GITHUB_CALLBACK_URL: Optional[str] = None
    AUTH_ALLOWED_LOGINS: str = ""
    AUTH_TOKEN_TTL_SECONDS: int = 28800       # a signed-in browser stays signed in for 8 hours
    # Local demo and tests only: lets anyone run write tools without signing in. Never set this
    # on a public deployment.
    AGENT_ALLOW_ANONYMOUS_WRITES: bool = False

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
