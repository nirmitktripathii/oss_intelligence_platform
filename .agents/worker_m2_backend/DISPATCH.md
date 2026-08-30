## 2026-08-29T11:41:02Z

You are worker_m2_backend, a teamwork_preview_worker for GitScout / OSS Terminal.
Working directory: e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\.agents\worker_m2_backend
Authoritative Request: e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\.agents\ORIGINAL_REQUEST.md
Project Blueprint: e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\PROJECT.md
Survey Specification: e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\.agents\explorer_backend_survey_2\handoff.md

Your exclusive write target directory:
- `e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\backend\`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your mission:
1. Build the complete production-grade FastAPI backend in `backend/`:
   - `backend/app/main.py`: FastAPI app factory, lifespan, CORS, OWASP security headers middleware, SlowAPI rate limiting, route registration.
   - `backend/app/config.py`: Pydantic BaseSettings loading environment variables.
   - `backend/app/database.py`: Async SQLAlchemy engine and session factory (supporting SQLite for local/tests and PostgreSQL for production).
   - `backend/app/models/`: SQLAlchemy ORM models (`issue.py`, `triage.py`, `subscription.py`, `billing.py`).
   - `backend/app/schemas/`: Pydantic v2 validation models (`issue.py`, `triage.py`, `bounty.py`, `notification.py`, `billing.py`).
   - `backend/app/scrapers/`:
     - `github_client.py`: Async GitHub client fetching open unassigned issues and searching bounties with ETag caching and rate limit handling.
     - `domain_registry.py`: Curated registry of 36 high-velocity repositories across 6 domains (AI/ML, Data, Web, Cloud/DevOps, Security, Systems).
     - `bounty_extractor.py`: Real-time regex & label parser extracting bounty amounts ($), sources (Polar, Algora, Sponsors), and URLs.
     - `classifier.py`: Tech stack tagger, difficulty scoring (Easy, Medium, Hard), Time-to-Solve (<1h, 2-4h, 6-12h), and Hourly ROI ($/hr) calculator.
     - `orchestrator.py`: Scraper runner that populates database with 50+ real, live, open unassigned issues with ZERO mock data. Also provide a CLI flag `--seed-live` or automated initial sync.
   - `backend/app/triage/`:
     - `ast_localizer.py`: Multi-language stack trace extractor and Python `ast` / symbol parser finding candidate files with confidence scores.
     - `repro_generator.py`: Standalone reproducible test script generator for reported bugs.
     - `fix_planner.py`: Step-by-step CONTRIBUTING.md-compliant fix blueprint.
   - `backend/app/dispatcher/`:
     - `base.py`: BaseNotifier interface & AlertPayload model.
     - `telegram.py`: Telegram Bot API notifier with inline keyboard buttons.
     - `discord.py`: Discord Webhook notifier with rich embeds.
     - `email.py`: Resend API notifier with aiosmtplib SMTP fallback.
     - `whatsapp.py`: Twilio WhatsApp notifier.
     - `router.py`: Subscription matching & broadcast queue.
   - `backend/app/billing/`:
     - `dodo.py`: Dodo Payments client & checkout session generator.
     - `lemonsqueezy.py`: Lemon Squeezy checkout initiator.
     - `webhook_handler.py`: HMAC signature verification and subscription state updater.
   - `backend/app/security/`:
     - `headers.py`: OWASP security headers middleware (CSP, HSTS, X-Frame-Options, etc.).
     - `rate_limiter.py`: SlowAPI rate limiting configuration.
   - `backend/app/api/v1/`:
     - `issues.py`, `triage.py`, `bounties.py`, `notifications.py`, `billing.py`, `health.py`, `router.py`.
   - `backend/requirements.txt` and `backend/pyproject.toml`.
2. Build comprehensive Pytest suite in `backend/tests/`:
   - `conftest.py`, `test_health.py`, `test_api_issues.py`, `test_api_triage.py`, `test_api_bounties.py`, `test_api_notifications.py`, `test_api_billing.py`, `test_scrapers.py`, `test_ast_localizer.py`, `test_dispatcher.py`, `test_security.py`.
3. Run the automated test suite (`pytest tests/ -v`) and verify 100% passing tests. Run the scraper to populate initial live data.
4. Write your handoff report to `e:\PORTFOLIO_PROJECTS\oss_intelligence_platform\.agents\worker_m2_backend\handoff.md` with full test results and send a message to parent when completed.
