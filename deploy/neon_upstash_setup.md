# Serverless Database & Cache Setup Guide ($0 Zero-Cost Infrastructure)
**Target Platform**: Neon Serverless PostgreSQL + Upstash Serverless Redis  
**Project**: GitScout / OSS Terminal  

---

## 1. Overview & Architectural Rationale

GitScout is designed to operate with **$0 initial fixed infrastructure costs** while delivering sub-millisecond query responses and auto-scaling to thousands of concurrent developer queries.

| Component | Provider | Free Tier Allocation | Role in GitScout |
| :--- | :--- | :--- | :--- |
| **Primary Relational DB** | **Neon PostgreSQL** | 0.5 GB storage, unlimited branching, 300 compute hours/mo | Persistent storage for Issues, Bounties, AI Triage Reports, Subscriptions |
| **Connection Pooling** | **Neon PgBouncer** | Built-in serverless pooling (Port 5432 / pooled endpoint) | Prevents connection exhaustion during traffic bursts |
| **In-Memory Cache & Rate Limiting** | **Upstash Redis** | 10,000 commands/day, 256 MB storage, Global REST/TCP | Request caching, ETag tracking, SlowAPI rate-limiting, Webhook idempotency |

```mermaid
flowchart LR
    FastAPI[FastAPI Backend\nRender / Fly.io] -->|asyncpg pooled| NeonPgBouncer[Neon PgBouncer\nport 5432]
    NeonPgBouncer --> NeonCompute[Neon Serverless Compute\nPostgres 16]
    FastAPI -->|HTTP REST / TCP| UpstashRedis[Upstash Serverless Redis]
    FastAPI -->|Webhooks| WebhookLog[(Idempotency Keys)]
```

---

## 2. Neon Serverless PostgreSQL Setup

### Step 2.1: Create Project & Database
1. Sign up at [https://neon.tech](https://neon.tech) (GitHub OAuth supported).
2. Click **Create Project**:
   - **Project Name**: `gitscout-production`
   - **Postgres Version**: `16` (recommended)
   - **Region**: Choose closest to your backend (e.g., `AWS us-east-1 (N. Virginia)` for Fly.io `iad` or `AWS us-west-2 (Oregon)` for Render `oregon`).
3. Under **Databases**, create a database named `gitscout`.

### Step 2.2: Obtain Connection Strings
In the Neon Console dashboard:
1. Ensure the **Pooled connection** checkbox is checked (uses PgBouncer on port `5432`).
2. Copy the connection string format:
   ```text
   postgresql://[user]:[password]@[neon-hostname]-pooler.[region].aws.neon.tech/gitscout?sslmode=require
   ```
3. For Python `asyncpg` compatibility in FastAPI, prefix with the SQLAlchemy asynchronous driver `postgresql+asyncpg://`:
   ```env
   DATABASE_URL=postgresql+asyncpg://[user]:[password]@[neon-hostname]-pooler.[region].aws.neon.tech/gitscout?ssl=require
   ```

### Step 2.3: Cold-Start Handling & Pool Configuration
On Neon's free tier, compute auto-suspends after 5 minutes of idle time. The GitScout SQLAlchemy engine handles wake-up gracefully via connection recycle and pre-ping:

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,       # Validates connection health before issuing queries
    pool_recycle=300,         # Recycles connections every 5 minutes
    pool_size=10,             # Fits comfortably in Neon free tier limits
    max_overflow=5,
    connect_args={
        "server_settings": {"application_name": "gitscout_api"}
    }
)
```

---

## 3. Upstash Serverless Redis Setup

### Step 3.1: Create Redis Database
1. Sign up at [https://upstash.com](https://upstash.com).
2. Click **Create Database**:
   - **Name**: `gitscout-cache`
   - **Type**: `Serverless (Pay-as-you-go / $0 free tier)`
   - **Region**: Select identical region to your Neon DB / Backend.
   - **Primary Store**: `Standard`
   - **Eviction**: `volatile-lru` (automatically evicts expired keys)
3. Click **Create**.

### Step 3.2: Obtain REST API & Standard Redis Credentials
Under the database **Details** tab:
1. **Standard TCP Redis URL**:
   ```env
   REDIS_URL=rediss://default:[password]@[upstash-endpoint].upstash.io:6379
   ```
2. **REST API Credentials** (for edge environments or serverless functions):
   ```env
   UPSTASH_REDIS_REST_URL=https://[upstash-endpoint].upstash.io
   UPSTASH_REDIS_REST_TOKEN=[your-upstash-rest-token]
   ```

---

## 4. Key Schema & Cache Invalidation Strategy

GitScout organizes Redis keys using clean hierarchical prefixes with explicit Time-To-Live (TTL):

| Key Pattern | Data Structure | TTL | Purpose |
| :--- | :--- | :--- | :--- |
| `gitscout:issues:domain:{domain}` | JSON String | 300s (5 min) | Cached list of open issues per engineering domain |
| `gitscout:triage:{repo_owner}:{repo_name}#{issue_num}` | JSON String | 86400s (24h) | Pre-computed AST file localization & repro snippets |
| `gitscout:bounties:top` | JSON String | 180s (3 min) | Cached top Hourly ROI bounties leaderboard |
| `gitscout:ratelimit:{ip_or_user_id}` | Counter | 60s (1 min) | SlowAPI sliding window rate limiter |
| `gitscout:webhook:idempotency:{event_id}` | String (`1`) | 604800s (7d) | Webhook deduplication key preventing double billing |
| `gitscout:etag:{repo_fullname}` | String (ETag) | 86400s (24h) | GitHub API ETag cache to avoid consuming rate limits |

### Python Cache Implementation Snippet

```python
import json
from typing import Optional, Any
import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

async def get_cached_triage(issue_id: str) -> Optional[dict]:
    cache_key = f"gitscout:triage:{issue_id}"
    data = await redis_client.get(cache_key)
    return json.loads(data) if data else None

async def set_cached_triage(issue_id: str, payload: dict, ttl_seconds: int = 86400):
    cache_key = f"gitscout:triage:{issue_id}"
    await redis_client.set(cache_key, json.dumps(payload), ex=ttl_seconds)
```

---

## 5. Unified Environment Configuration (.env)

Below is the complete, copy-paste `.env` template combining Neon PostgreSQL and Upstash Redis:

```env
# ==========================================
# GITSCOUT ZERO-COST CLOUD CONFIGURATION
# ==========================================
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="GitScout / OSS Terminal"
VERSION="1.0.0"
API_V1_STR="/api/v1"

# --- Neon Serverless PostgreSQL ---
# Replace with your pooled connection URI:
DATABASE_URL="postgresql+asyncpg://neondb_owner:npg_SecretPass123@ep-cool-butterfly-123456-pooler.us-east-1.aws.neon.tech/gitscout?ssl=require"

# --- Upstash Serverless Redis ---
REDIS_URL="rediss://default:upstash_secret_pass@us1-clean-tiger-12345.upstash.io:6379"
UPSTASH_REDIS_REST_URL="https://us1-clean-tiger-12345.upstash.io"
UPSTASH_REDIS_REST_TOKEN="AZ12AAIjcDE..."

# --- Frontend & CORS ---
FRONTEND_URL="https://gitscout.vercel.app"
CORS_ORIGINS="https://gitscout.vercel.app,http://localhost:3000,http://127.0.0.1:3000"

# --- Scraper & GitHub API ---
GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere" # Increases rate limit from 60 to 5,000 req/hr
GITHUB_API_BASE="https://api.github.com"
SCRAPE_INTERVAL_MINUTES=30
DEFAULT_REPO_LIMIT=20

# --- Multi-Channel Dispatchers ---
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
TELEGRAM_CHAT_ID="@gitscout_alerts"
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
RESEND_API_KEY="re_123456789_abcdef"
RESEND_FROM_EMAIL="alerts@gitscout.dev"

# --- Monetization & Webhooks ---
DODO_PAYMENTS_API_KEY="dodo_test_12345"
DODO_PAYMENTS_WEBHOOK_KEY="whsec_dodo_12345"
DODO_ENVIRONMENT="test_mode"
LEMON_SQUEEZY_API_KEY="ls_test_12345"
LEMON_SQUEEZY_STORE_ID="12345"
LEMON_SQUEEZY_WEBHOOK_SECRET="whsec_ls_12345"
```

---

## 6. Verification & Health Monitoring

Run these quick checks after configuring your environment:

1. **Verify Database Connection**:
   ```bash
   python -c "import asyncio; from backend.app.database import engine; asyncio.run(engine.connect()); print('[OK] Neon PostgreSQL Connected Successfully!')"
   ```

2. **Verify Upstash Redis Connection**:
   ```bash
   python -c "import asyncio, redis.asyncio as aioredis; r = aioredis.from_url('rediss://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379'); asyncio.run(r.ping()); print('[OK] Upstash Redis Connected Successfully!')"
   ```

3. **Query Health Endpoint**:
   ```bash
   curl -X GET http://localhost:8000/api/v1/health
   # Expected Output: {"status":"healthy","issues_count":54,"db_connected":true,"version":"1.0.0"}
   ```
