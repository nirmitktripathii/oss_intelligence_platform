# Handoff Report: High-Throughput FastAPI Backend & AI Triage Engine (R2, R5)

**Agent ID**: `explorer_backend_survey_2`  
**Role**: Backend Architecture Investigator & API Designer  
**Scope**: Technical Specifications, Module Architecture, Scraping & Triage Engine, Security & Testing Strategy for GitScout / OSS Intelligence Platform  
**Target Milestone**: M2 (High-Throughput Backend & AI Triage Engine) & Full Stack Integration (R2, R5)  

---

## 1. Observation

### 1.1 Requirements Observed in `ORIGINAL_REQUEST.md`
- **R2: High-Throughput Python (FastAPI) Backend & AI Triage Engine**:
  - **Live Scraper Engine**: Real-time crawling of 100% live, open, unassigned GitHub issues and funded bounties across 6 core domains (AI/ML, Data, Web, Cloud/DevOps, Security, Systems) with ZERO synthetic mock data (50+ real issues indexed).
  - **AI Triage & Localization**: AST/heuristic file localizer, minimal bug reproduction snippet generator, and `CONTRIBUTING.md`-compliant fix planner.
  - **Multi-Channel Dispatcher**: Dedicated notifiers for Telegram Bot API, Discord Webhook / Bot, Transactional Email (Resend API with SMTP fallback), and Twilio WhatsApp Pro.
  - **RESTful Endpoints**: Clean API routes for `/api/v1/issues`, `/api/v1/triage/{id}`, `/api/v1/bounties`, `/api/v1/notifications/subscribe`, and `/api/v1/billing/checkout`.
- **R5: Security, Performance & Rigorous Automated Testing**:
  - Strict input validation via Pydantic v2, CORS whitelisting, rate-limiting, and OWASP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
  - Comprehensive automated test suite in `backend/tests/` with 100% passing `pytest` suite for API routes, scrapers, classifier, and dispatchers.

### 1.2 External APIs & Ecosystem Reality
- **GitHub API**:
  - Direct repository issues endpoint `GET /repos/{owner}/{repo}/issues?state=open&assignee=none&per_page=30` operates under the general core rate limit (5,000 req/hr authenticated, 60 req/hr unauthenticated).
  - Search API `GET /search/issues?q=is:issue+is:open+no:assignee...` operates under a stricter limit (30 req/min authenticated, 10 req/min unauthenticated).
  - Conditional requests via `If-None-Match: <ETag>` return `304 Not Modified` and preserve rate limit quotas.
- **Polar.sh & Algora Bounty Tracking**:
  - Algora's standalone `console.algora.io` endpoints are deprecated; however, bounties are actively tracked via GitHub issue labels (`label:bounty`, `label:funded`, `label:algora`, `label:polar`) and bot comments (`/bounty $amount`, `💵 $amount bounty on this issue`, `Funding on Polar: $amount`).
  - Scraper must parse both structured labels and unstructured markdown text to extract exact USD amounts, sources, and payout URLs.
- **Payment Providers (Dodo Payments & Lemon Squeezy)**:
  - **Dodo Payments**: Python async client `AsyncDodoPayments(bearer_token=..., environment="test_mode"|"live_mode")` creating checkout sessions via `client.checkout_sessions.create(product_cart=[{"product_id": "...", "quantity": 1}])` returning `session.checkout_url`.
  - **Lemon Squeezy**: JSON:API `POST https://api.lemonsqueezy.com/v1/checkouts` with `Authorization: Bearer <KEY>` returning hosted checkout URL.
- **Dispatch Providers**:
  - **Telegram**: `POST https://api.telegram.org/bot<TOKEN>/sendMessage` supporting HTML / MarkdownV2 formatting and `inline_keyboard` interactive buttons.
  - **Discord**: `POST https://discord.com/api/webhooks/{id}/{token}` supporting rich embeds with hex colors, fields, and footers.
  - **Resend Email**: `POST https://api.resend.com/emails` with fallback to `aiosmtplib` standard SMTP.
  - **Twilio WhatsApp**: `POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json` with basic auth.

---

## 2. Logic Chain

```
[Requirement: 50+ Real Live Issues Across 6 Domains with Zero Mock Fallbacks]
       │
       ▼
[Observation: GitHub Repo Issues API is faster and has higher rate limit than global Search API]
       │
       ▼
[Architectural Choice: Domain Registry with Curated High-Velocity Repos + Global Bounty Search + ETag Caching]
       │
       ▼
[Requirement: AST File Localization, Repro Snippets & Fix Plans]
       │
       ▼
[Architectural Choice: Multi-Stage Heuristic & AST Engine (Stack Trace Parsing + Path Regex + Tree-sitter / AST Identifier Matching + Git Tree Verification)]
       │
       ▼
[Requirement: Instant Multi-Channel Alerts]
       │
       ▼
[Architectural Choice: Asynchronous Dispatch Pipeline with Uniform Alert Payload & Provider Adapters (Telegram, Discord, Resend/SMTP, Twilio)]
       │
       ▼
[Requirement: Production-Ready Security, CORS, Rate Limiting & 100% Pytest Suite]
       │
       ▼
[Architectural Choice: FastAPI + Pydantic v2 Models + OWASP Middleware + SlowAPI + Async SQLAlchemy + Hermetic Fixtures with Respx]
```

### 2.1 Live Scraper Engine Architecture
1. **Curated Domain Repositories (6 Domains, 36 Target Repos)**:
   - **AI/ML**: `langchain-ai/langchain`, `huggingface/transformers`, `vllm-project/vllm`, `ollama/ollama`, `microsoft/autogen`, `chroma-core/chroma`
   - **Data**: `pydantic/pydantic`, `pola-rs/polars`, `duckdb/duckdb`, `apache/arrow`, `dbt-labs/dbt-core`, `pandas-dev/pandas`
   - **Web**: `fastapi/fastapi`, `pallets/flask`, `encode/httpx`, `vercel/next.js`, `facebook/react`, `trpc/trpc`
   - **Cloud/DevOps**: `kubernetes/kubernetes`, `hashicorp/terraform`, `helm/helm`, `ansible/ansible`, `moby/moby`, `prometheus/prometheus`
   - **Security**: `OWASP/CheatSheetSeries`, `trufflesecurity/trufflehog`, `sqlmapproject/sqlmap`, `projectdiscovery/nuclei`, `wpscanteam/wpscan`, `SigmaHQ/sigma`
   - **Systems**: `rust-lang/rust`, `tokio-rs/tokio`, `redis/redis`, `neovim/neovim`, `ziglang/zig`, `tauri-apps/tauri`
2. **Dual-Mode Harvesting**:
   - **Direct Mode**: Queries `GET /repos/{owner}/{repo}/issues?state=open&assignee=none&per_page=15` across registered repositories. Guarantees 100% real, open, unassigned issues.
   - **Bounty Search Mode**: Queries `GET /search/issues?q=is:issue+is:open+no:assignee+(label:bounty+OR+label:funded+OR+"bounty"+in:title,body)&per_page=30` to discover funded bounties globally.
3. **Extraction & Classification Pipeline**:
   - **Bounty Regex Extractor**: Extracts numerical bounty values (`$100`, `💵 $250`, `/bounty $500`, `bounty: 500 USD`) and tags source (`Polar`, `Algora`, `GitHub Sponsors`, `GitScout Index`).
   - **Difficulty Classifier**: Evaluates issue labels (`good first issue`, `beginner`, `documentation` vs `help wanted`, `bug` vs `hard`, `rfc`, `performance`), description word count, stack trace presence, and code block complexity.
   - **Time-to-Solve & Hourly ROI**:
     - Easy: 0.5 – 1.0 hr
     - Medium: 2.0 – 4.0 hr
     - Hard: 6.0 – 12.0 hr
     - `Hourly ROI = Bounty USD / Estimated Hours` (e.g. $200 / 2h = $100/hr).
4. **Storage & Upsert**:
   - Asynchronous SQLAlchemy models backed by SQLite (for development/testing) and PostgreSQL (for production).
   - Natural composite key `repo_owner/repo_name#issue_number` prevents duplicates and enables fast in-place updates.

### 2.2 AI Triage & AST File Localizer Engine
1. **Stack Trace Extraction**:
   - Python: `r'File "([^"]+)", line (\d+), in (\w+)'`
   - JS/TypeScript: `r'at (?:[^\s]+ \()?([^:]+):(\d+):(\d+)\)?'`
   - Go: `r'(?:[^\s]+)\.([^\s]+)\(.*\)\n\s+([^:]+):(\d+)'`
   - Rust: `r'at ([^:]+\.rs):(\d+):(\d+)'`
2. **Path & Symbol Identifier Analysis**:
   - Extracts candidate file paths from markdown inline code and block quotes.
   - Python `ast.parse` and regex symbol extractors identify class names (e.g. `BaseModel`, `APIRoute`), function names, decorator references, and exception types.
   - Cross-references candidate paths against repository tree structure (via GitHub Tree API or cached repo manifests) to calculate confidence score (0.0 to 1.0).
3. **Minimal Bug Reproduction Generator**:
   - Isolates problem code snippets from issue description.
   - Wraps snippet in a self-contained test script with necessary imports, input fixture, execution block, and assertion of failure mode.
   - Outputs ready-to-run code snippet with execution instructions.
4. **CONTRIBUTING.md Fix Planner**:
   - Generates structured 4-step actionable blueprint conforming to open-source contribution best practices:
     - Step 1: Environment & Branching (`git checkout -b fix/issue-XYZ`)
     - Step 2: Target File & Function Localization + Proposed Code Modification
     - Step 3: Test Verification Command (`pytest tests/... -k ...`)
     - Step 4: Quality Gate & PR Submission formatting.

### 2.3 Multi-Channel Dispatcher Engine
- **Unified Alert Model**:
  ```python
  class AlertPayload(BaseModel):
      issue_id: str
      title: str
      repo: str
      html_url: str
      domain: IssueDomain
      tech_stack: List[str]
      difficulty: IssueDifficulty
      estimated_hours: float
      bounty_usd: Optional[float] = None
      hourly_roi: Optional[float] = None
      summary: str
      suggested_files: List[str] = []
  ```
- **Provider Adapters**:
  - `TelegramNotifier`: Dispatches formatted messages with inline action buttons (`View on GitHub`, `Open Triage Drawer`, `Claim Bounty`).
  - `DiscordNotifier`: Dispatches rich embeds color-coded by domain with difficulty badges and bounty highlights.
  - `EmailNotifier`: Renders clean HTML template via Resend API (`api.resend.com/emails`), with automatic fallback to `aiosmtplib` if Resend key is unavailable.
  - `TwilioWhatsAppNotifier`: Dispatches concise WhatsApp notifications with direct action links for Pro subscribers.
- **Subscription Matching & Broadcast Queue**:
  - Non-blocking background worker evaluates new/updated issues against subscriber preferences (domain filter, min bounty, difficulty filter, keyword match) and dispatches concurrently with exponential backoff retries.

### 2.4 REST API & Security Architecture
- **FastAPI Application Structure**:
  - Modular router structure (`/api/v1/issues`, `/api/v1/triage`, `/api/v1/bounties`, `/api/v1/notifications`, `/api/v1/billing`, `/api/v1/health`).
  - Pydantic v2 strict models for query parameters, request bodies, and responses.
  - Custom Security Headers Middleware setting OWASP-compliant headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
  - CORS Middleware configured with explicit origin whitelists.
  - SlowAPI Rate Limiter with endpoint-specific rate quotas.

---

## 3. Caveats & Edge Cases

1. **GitHub API Rate Limits**:
   - Without a `GITHUB_TOKEN`, the unauthenticated rate limit is 60 requests/hour.
   - **Mitigation**: The backend must support optional `GITHUB_TOKEN` in `.env`, implement ETag conditional requests (`If-None-Match`), cache repository responses in-memory / SQLite, and stagger periodic scraping cycles.
2. **Algora & Polar API Availability**:
   - Standalone Algora bounty discovery API endpoints have been deprecated by Algora in favor of recruitment features.
   - **Mitigation**: The scraper engine extracts bounties directly from GitHub issue metadata, labels, and issue body comments posted by Algora/Polar bots across repositories, ensuring 100% live data accuracy.
3. **Tree-sitter vs Python `ast` Module**:
   - Python's standard `ast` module handles Python code analysis natively without binary compilation dependencies.
   - **Mitigation**: Use Python `ast` for Python issues combined with robust regex-based multi-language parsers for TypeScript, Go, and Rust, ensuring zero runtime C-extension compile failures on Windows/Linux.
4. **Dispatcher Environment Variables**:
   - In development/testing environments, notification tokens (Telegram, Discord, Resend, Twilio) may be unconfigured.
   - **Mitigation**: Dispatchers gracefully detect missing credentials, log detailed dispatch intent in development mode, and return simulated delivery status without raising unhandled exceptions.

---

## 4. Conclusion & Technical Specifications

### 4.1 Backend Directory Layout (`backend/`)
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, lifespan, middleware
│   ├── config.py                   # Pydantic BaseSettings environment configuration
│   ├── database.py                 # Async SQLAlchemy engine, sessionmaker, Base
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── issue.py                # Issue, Bounty, Label models
│   │   ├── triage.py               # TriageReport, LocalizedFile models
│   │   ├── subscription.py         # NotificationSubscription model
│   │   └── billing.py              # BillingSubscription model
│   ├── schemas/                    # Pydantic v2 validation models
│   │   ├── __init__.py
│   │   ├── issue.py                # IssueResponse, IssueFilterParams, PaginatedIssues
│   │   ├── triage.py               # TriageResponse, FixPlanStep, LocalizedFileSchema
│   │   ├── bounty.py               # BountyResponse, BountyListResponse
│   │   ├── notification.py         # SubscriptionCreate, SubscriptionResponse
│   │   └── billing.py              # CheckoutRequest, CheckoutResponse, WebhookPayload
│   ├── scrapers/                   # Real-time scraper engine
│   │   ├── __init__.py
│   │   ├── github_client.py        # Async GitHub API client (REST & Search)
│   │   ├── domain_registry.py      # Curated repo registry across 6 domains
│   │   ├── bounty_extractor.py     # Regex bounty parsing & source attribution
│   │   ├── classifier.py           # Tech-stack tagging & difficulty scoring
│   │   └── orchestrator.py         # Periodic scraper runner & DB sync
│   ├── triage/                     # AI Triage & AST Localizer
│   │   ├── __init__.py
│   │   ├── ast_localizer.py        # Stack trace & AST symbol extraction
│   │   ├── repro_generator.py      # Standalone bug reproduction snippet builder
│   │   └── fix_planner.py          # Step-by-step CONTRIBUTING.md fix blueprint
│   ├── dispatcher/                 # Multi-channel notification engine
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseNotifier interface & AlertPayload
│   │   ├── telegram.py             # Telegram Bot API notifier
│   │   ├── discord.py              # Discord Webhook notifier
│   │   ├── email.py                # Resend API + aiosmtplib SMTP fallback
│   │   ├── whatsapp.py             # Twilio WhatsApp Pro notifier
│   │   └── router.py               # Subscription matching & broadcast queue
│   ├── billing/                    # Monetization engine
│   │   ├── __init__.py
│   │   ├── dodo.py                 # Dodo Payments async client
│   │   ├── lemonsqueezy.py         # Lemon Squeezy API client
│   │   └── webhook_handler.py      # Signature verification & event processing
│   ├── security/                   # Security & middleware
│   │   ├── __init__.py
│   │   ├── headers.py              # OWASP security headers middleware
│   │   └── rate_limiter.py         # SlowAPI rate limiter setup
│   └── api/                        # REST API routes
│       ├── __init__.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── router.py           # Unified v1 router
│       │   ├── issues.py           # /api/v1/issues endpoints
│       │   ├── triage.py           # /api/v1/triage endpoints
│       │   ├── bounties.py         # /api/v1/bounties endpoints
│       │   ├── notifications.py    # /api/v1/notifications endpoints
│       │   ├── billing.py          # /api/v1/billing endpoints
│       │   └── health.py           # /api/v1/health endpoint
├── tests/                          # Automated Pytest Suite
│   ├── __init__.py
│   ├── conftest.py                 # Async fixtures, mock client, test DB
│   ├── test_health.py              # Health check tests
│   ├── test_api_issues.py          # Issues search, filtering, pagination tests
│   ├── test_api_triage.py          # Triage retrieval and on-demand trigger tests
│   ├── test_api_bounties.py        # Bounty listing and ROI sorting tests
│   ├── test_api_notifications.py   # Subscription management tests
│   ├── test_api_billing.py         # Checkout & webhook verification tests
│   ├── test_scrapers.py            # GitHub scraper & bounty extractor tests
│   ├── test_ast_localizer.py       # AST parsing & repro generator tests
│   ├── test_dispatcher.py          # Multi-channel notifier tests
│   └── test_security.py            # Security headers, CORS, and rate limit tests
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Pytest & Ruff configurations
└── README.md                       # Backend documentation & setup guide
```

### 4.2 Core API Schema Contracts

#### 1. Issues & Bounties
```python
# backend/app/schemas/issue.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from enum import Enum
from typing import List, Optional
from datetime import datetime

class IssueDomain(str, Enum):
    AI_ML = "AI/ML"
    DATA = "Data"
    WEB = "Web"
    CLOUD_DEVOPS = "Cloud/DevOps"
    SECURITY = "Security"
    SYSTEMS = "Systems"

class IssueDifficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class LabelSchema(BaseModel):
    name: str
    color: str
    description: Optional[str] = None

class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., example="fastapi/fastapi#12345")
    repo_owner: str = Field(..., example="fastapi")
    repo_name: str = Field(..., example="fastapi")
    issue_number: int = Field(..., example=12345)
    title: str
    body: Optional[str] = ""
    html_url: str
    author: str
    domain: IssueDomain
    tech_stack: List[str] = Field(default_factory=list)
    difficulty: IssueDifficulty
    estimated_hours: float
    has_bounty: bool = False
    bounty_amount_usd: Optional[float] = None
    bounty_source: Optional[str] = None
    bounty_url: Optional[str] = None
    hourly_roi: Optional[float] = None
    state: str = "open"
    comments_count: int = 0
    github_created_at: datetime
    github_updated_at: datetime
    labels: List[LabelSchema] = Field(default_factory=list)

class PaginatedIssuesResponse(BaseModel):
    items: List[IssueResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

#### 2. AI Triage & Workbench
```python
# backend/app/schemas/triage.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

class LocalizedFile(BaseModel):
    file_path: str = Field(..., example="fastapi/routing.py")
    line_range: Optional[str] = Field(None, example="145-180")
    confidence: float = Field(..., ge=0.0, le=1.0, example=0.92)
    rationale: str = Field(..., example="Stack trace and method definition match APIRoute.get_route_handler")

class FixPlanStep(BaseModel):
    step_number: int
    title: str
    description: str
    code_snippet: Optional[str] = None
    verification_command: Optional[str] = None

class TriageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_id: str
    summary: str
    root_cause_analysis: str
    localized_files: List[LocalizedFile]
    reproduction_code: str
    reproduction_lang: str = "python"
    reproduction_instructions: str
    fix_plan_steps: List[FixPlanStep]
    contributing_guidelines_summary: Optional[str] = None
    created_at: datetime
```

#### 3. Notifications & Subscriptions
```python
# backend/app/schemas/notification.py
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from enum import Enum
from typing import List, Optional

class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class SubscriptionCreate(BaseModel):
    channel: ChannelType
    destination: str = Field(..., description="Telegram Chat ID, Discord Webhook URL, Email, or WhatsApp Number")
    domains: Optional[List[str]] = Field(default=None, description="List of domains or null for all")
    min_bounty: float = Field(default=0.0, ge=0.0)
    difficulty: Optional[List[str]] = Field(default=None)
    tech_stacks: Optional[List[str]] = Field(default=None)

class SubscriptionResponse(SubscriptionCreate):
    id: int
    is_active: bool
    created_at: str
```

#### 4. Billing & Pro Checkout
```python
# backend/app/schemas/billing.py
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional

class PaymentProvider(str, Enum):
    DODO = "dodopayments"
    LEMON_SQUEEZY = "lemonsqueezy"

class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., example="pro_monthly")
    customer_email: EmailStr
    provider: PaymentProvider = PaymentProvider.DODO
    success_url: Optional[str] = "http://localhost:3000/dashboard?checkout=success"
    cancel_url: Optional[str] = "http://localhost:3000/pricing?checkout=cancelled"

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    provider: PaymentProvider
```

### 4.3 Key Dependencies Specification (`requirements.txt`)
```txt
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.2.0
sqlalchemy[asyncio]>=2.0.30
aiosqlite>=0.20.0
asyncpg>=0.29.0
httpx>=0.27.0
apscheduler>=3.10.4
slowapi>=0.1.9
resend>=2.0.0
aiosmtplib>=3.0.1
python-dotenv>=1.0.1
pytest>=8.2.0
pytest-asyncio>=0.23.7
respx>=0.21.1
pytest-cov>=5.0.0
```

---

## 5. Verification Method

### 5.1 Verification Commands for Independent Quality Gate

1. **Automated Unit & Integration Test Suite**:
   ```bash
   cd backend
   pytest tests/ -v --cov=app --cov-report=term-missing
   ```
   - **Success Condition**: 100% of test cases pass with zero failures or unhandled exceptions.

2. **Live Scraper Engine & Database Population**:
   ```bash
   cd backend
   python -m app.scrapers.orchestrator --dry-run
   ```
   - **Success Condition**: Scrapes and indexes >50 real open unassigned GitHub issues across the 6 domains (AI/ML, Data, Web, Cloud/DevOps, Security, Systems), verifying all issues have valid titles, URLs, and labels, with zero synthetic mock data.

3. **REST API Endpoint Verification**:
   - `GET http://localhost:8000/api/v1/health` -> HTTP 200 `{"status": "healthy", "issues_count": N, "db_connected": true}`
   - `GET http://localhost:8000/api/v1/issues?domain=AI/ML&page=1&page_size=10` -> HTTP 200 with paginated JSON items.
   - `GET http://localhost:8000/api/v1/bounties` -> HTTP 200 with bounties sorted by `hourly_roi`.
   - `GET http://localhost:8000/api/v1/triage/{issue_id}` -> HTTP 200 with localized files, repro snippet, and fix plan.
   - `POST http://localhost:8000/api/v1/notifications/subscribe` -> HTTP 201 with subscription ID.
   - `POST http://localhost:8000/api/v1/billing/checkout` -> HTTP 200 with valid `checkout_url`.

4. **Security & Header Compliance**:
   ```bash
   curl -I http://localhost:8000/api/v1/health
   ```
   - **Success Condition**: Response headers must contain:
     - `Content-Security-Policy`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Strict-Transport-Security`
     - `Referrer-Policy: strict-origin-when-cross-origin`
     - `Permissions-Policy`

5. **Invalidation Conditions**:
   - If mock or synthetic data is returned by `/api/v1/issues`.
   - If any endpoint lacks Pydantic v2 validation or raises an unhandled 500 error on malformed input.
   - If tests fail when run in a hermetic environment without external network access.
