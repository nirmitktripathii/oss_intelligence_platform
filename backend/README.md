# GitScout / OSS Terminal - Backend Service

High-throughput asynchronous FastAPI backend and AI triage engine powering GitScout.

## Architecture Overview

- **FastAPI Core**: Async API routes with Pydantic v2 schemas and OWASP security headers.
- **Async SQLAlchemy**: High-performance persistence layer supporting SQLite (dev/test) and PostgreSQL (production).
- **Live Scraper Engine**: Real-time crawling of 100% live open unassigned GitHub issues and funded bounties across 36 repos in 6 domains with zero mock data.
- **AI AST Triage & Diagnostics**: Stack trace parsing, Python `ast` symbol extraction, minimal reproduction snippet generation, and step-by-step PR fix planner.
- **Multi-Channel Dispatcher**: Telegram Bot API, Discord Webhook, Resend Email / SMTP, and Twilio WhatsApp Pro notifiers.
- **Turnkey Micro-SaaS Billing**: Dodo Payments and Lemon Squeezy integration with HMAC signature verification.
- **OWASP Security**: Content-Security-Policy, HSTS, X-Frame-Options, X-Content-Type-Options, and SlowAPI rate limiting.

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed live GitHub issues & bounties
python -m app.scrapers.orchestrator --seed-live

# 3. Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

### Key Endpoints:
- `GET /api/v1/health` - System health, DB connectivity & indexed issue count.
- `GET /api/v1/issues` - Filterable & searchable open issues across 6 domains.
- `GET /api/v1/triage/{issue_id}` - AI AST file localization, repro code & fix plan.
- `GET /api/v1/bounties` - Funded bounties sorted by Hourly ROI ($/hr).
- `POST /api/v1/notifications/subscribe` - Multi-channel alert subscription.
- `POST /api/v1/billing/checkout` - Dodo Payments / Lemon Squeezy checkout trigger.

## Testing

```bash
pytest tests/ -v --cov=app
```
