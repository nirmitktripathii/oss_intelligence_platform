# E2E Test Infra: GitScout / OSS Intelligence Platform

## Test Philosophy
- **Opaque-Box & Requirement-Driven**: Tests derive directly from `ORIGINAL_REQUEST.md` and user-facing API/UI contracts without depending on internal implementation details.
- **Methodology**: 4-Tier verification incorporating Category-Partition, Boundary Value Analysis (BVA), Pairwise Combinatorial Testing, and Real-World Workload Scenarios.
- **Integrity Enforcement**: 100% real live data verification — any synthetic mock or fake issue is treated as a critical integrity failure.

---

## Feature Inventory & Test Coverage Matrix

| # | Feature Area | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|--------------|:----------------:|:-----------------:|:-----------------:|:-----------------:|
| F1 | Market Research & Strategy Docs (R1, R7) | 5 | 5 | ✓ | ✓ |
| F2 | Live Scraper Engine (6 Domains, 36 Repos) | 6 | 6 | ✓ | ✓ |
| F3 | AI AST Localizer & Repro Generator | 5 | 5 | ✓ | ✓ |
| F4 | Multi-Channel Dispatchers (TG, DC, Resend, WA) | 5 | 5 | ✓ | ✓ |
| F5 | FastAPI REST APIs & Security Headers | 6 | 6 | ✓ | ✓ |
| F6 | Next.js 14 Dashboard & Theme Switcher | 5 | 5 | ✓ | ✓ |
| F7 | Interactive Issue Explorer & Filters | 5 | 5 | ✓ | ✓ |
| F8 | AI Workbench Drawer & Localized Files | 5 | 5 | ✓ | ✓ |
| F9 | Bounty & Hourly ROI Calculator | 5 | 5 | ✓ | ✓ |
| F10 | Notification Manager & Pro Pricing Modals | 5 | 5 | ✓ | ✓ |
| F11 | Graphify Knowledge Graph Mapping & Viewer | 5 | 5 | ✓ | ✓ |
| F12 | Turnkey Cloud Deployment & Docker Compose | 5 | 5 | ✓ | ✓ |

**Total Test Targets**:
- Tier 1: 62 test cases
- Tier 2: 62 test cases
- Tier 3: 16 cross-feature interaction cases
- Tier 4: 8 comprehensive end-to-end user journeys
- **Total Test Suite**: 148 test cases

---

## Test Architecture

### 1. Test Runner & Execution
- **Backend Test Runner**: `pytest backend/tests/ -v --cov=app --cov-report=term-missing`
- **E2E Integration Runner**: Python-based test orchestrator `tests/e2e/test_e2e_suite.py` executing direct HTTP assertions against FastAPI endpoints and validating file artifacts.
- **Frontend Quality Gate**: `npm run lint` and `npx tsc --noEmit` and `npm run build` in `frontend/`.

### 2. Directory Layout
```
tests/
├── e2e/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_tier1_features.py       # Tier 1: Happy path isolated feature tests
│   ├── test_tier2_boundaries.py     # Tier 2: Boundary value, edge cases, error modes
│   ├── test_tier3_pairwise.py       # Tier 3: Cross-feature interaction tests
│   ├── test_tier4_scenarios.py      # Tier 4: Real-world contributor workflows
│   └── test_audit_integrity.py     # Zero-mock and forensic integrity validation
└── run_e2e.py                       # Unified E2E test runner CLI
```

---

## Real-World Application Scenarios (Tier 4)

| # | Scenario Name | Features Exercised | User Journey Description |
|---|---------------|--------------------|--------------------------|
| 1 | High-Yield Bounty Hunting | F2, F5, F7, F8, F9 | User filters for funded issues in AI/ML domain with >$100 bounty, sorts by Hourly ROI, inspects top issue via AI Workbench, copies reproduction script, and reviews CONTRIBUTING.md checklist. |
| 2 | Good First Issue Onboarding | F2, F5, F7, F8 | New contributor filters for "Good First Issue" in Web domain (<30m time to solve), locates target files, and follows the 4-step PR submission guide. |
| 3 | Instant Multi-Channel Alerting | F4, F5, F10 | User subscribes to Telegram & Discord alerts for Security domain bounties >= $50; backend scraper finds a new issue and dispatches formatted alert payloads with inline links. |
| 4 | Pro Tier Monetization & Upgrade | F5, F6, F10 | User accesses Pro pricing modal, toggles annual discount, selects Dodo Payments / Lemon Squeezy gateway, and triggers checkout session. |
| 5 | Deep Codebase AST Exploration | F3, F8, F11 | Developer clicks "Explore in Graphify" from localized file in Workbench drawer, opening the interactive AST knowledge graph to inspect dependency blast radius. |
| 6 | Zero-Cost Infrastructure Verification | F12 | DevOps engineer validates Dockerfile, docker-compose.yml, vercel.json, render.yaml, and fly.toml configs for syntax, port mappings, and environment variables. |
| 7 | Multi-Theme Ergonomics & Accessibility | F6, F7, F8 | User toggles Dark, Light, and System themes across main dashboard, drawer, and modals without hydration flicker or color contrast breakage. |
| 8 | Strategic Due Diligence Audit | F1, F5, F12 | Potential buyer reviews competitive analysis, SEO/GEO playbooks, and Acquire.com valuation models in docs, verifying technical and financial completeness. |
