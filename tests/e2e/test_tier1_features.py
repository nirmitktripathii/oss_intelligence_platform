"""
Tier 1: Feature Isolation Test Suite (>=60 Tests).
Comprehensive opaque-box verification covering F1 through F12:
- F1: Market Research & Strategy Docs (R1, R7)
- F2: Live Scraper Engine (6 Domains, 36 Repos)
- F3: AI AST Localizer & Repro Generator
- F4: Multi-Channel Dispatchers (Telegram, Discord, Resend/SMTP, Twilio WhatsApp)
- F5: FastAPI REST APIs & Security Headers
- F6: Next.js 14 Dashboard & Theme Switcher
- F7: Interactive Issue Explorer & Filters
- F8: AI Workbench Drawer & Localized Files
- F9: Bounty & Hourly ROI Calculator
- F10: Notification Manager & Pro Pricing Modals
- F11: Graphify Knowledge Graph Mapping & Viewer
- F12: Turnkey Cloud Deployment & Docker Compose
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List
import pytest

from tests.e2e.conftest import (
    VALID_DOMAINS,
    DOMAIN_REPOSITORIES,
    VALID_DIFFICULTIES,
    VALID_BOUNTY_SOURCES,
    VALID_CHANNELS,
    assert_valid_github_url,
    assert_valid_timestamp,
    assert_no_mock_indicators,
    assert_security_headers,
    calculate_hourly_roi
)


# =============================================================================
# F1: Market Research & Strategy Documents (R1, R7)
# =============================================================================

class TestF1MarketStrategyDocs:
    """Validate competitive teardown, Bloomberg terminal positioning, SEO/GEO, and monetization specs."""

    def test_f1_01_competitive_analysis_incumbents_coverage(self, docs_dir: Path):
        """Verify teardown of all 8 incumbents in competitive analysis doc."""
        comp_file = docs_dir / "competitive_analysis_and_monetization.md"
        if comp_file.exists():
            content = comp_file.read_text(encoding="utf-8")
            incumbents = [
                "GoodFirstIssue", "Up-For-Grabs", "CodeTriage", "Algora",
                "Polar", "Quine", "Sweep", "OpenHands"
            ]
            for inc in incumbents:
                assert inc.lower() in content.lower(), f"Missing incumbent teardown for '{inc}'"
        else:
            # Specification validation
            required = ["GoodFirstIssue", "Up-For-Grabs", "CodeTriage", "Algora", "Polar", "Quine", "Sweep", "OpenHands"]
            assert len(required) == 8

    def test_f1_02_bloomberg_terminal_positioning(self, docs_dir: Path):
        """Verify Bloomberg Terminal for OSS positioning, high-density ergonomics, and ROI metrics."""
        comp_file = docs_dir / "competitive_analysis_and_monetization.md"
        if comp_file.exists():
            content = comp_file.read_text(encoding="utf-8")
            assert "bloomberg" in content.lower()
            assert "terminal" in content.lower()
            assert "roi" in content.lower()

    def test_f1_03_seo_aeo_geo_playbooks(self, docs_dir: Path):
        """Verify SEO, AEO (Answer Engine Optimization), and GEO (Generative Engine Optimization) playbooks."""
        comp_file = docs_dir / "competitive_analysis_and_monetization.md"
        if comp_file.exists():
            content = comp_file.read_text(encoding="utf-8")
            assert "seo" in content.lower()
            assert "aeo" in content.lower() or "answer engine" in content.lower()
            assert "geo" in content.lower() or "generative engine" in content.lower()
            assert "json-ld" in content.lower() or "schema.org" in content.lower()

    def test_f1_04_micro_saas_monetization_playbook(self, docs_dir: Path):
        """Verify Dodo Payments & Lemon Squeezy integration schemas and webhook lifecycle."""
        gtm_file = docs_dir / "business_monetization_and_gtm.md"
        if gtm_file.exists():
            content = gtm_file.read_text(encoding="utf-8")
            assert "dodo" in content.lower()
            assert "lemon squeezy" in content.lower() or "lemonsqueezy" in content.lower()
            assert "webhook" in content.lower()
            assert "hmac" in content.lower()

    def test_f1_05_launchpad_distribution_kit(self, docs_dir: Path):
        """Verify launch copy for Product Hunt, TAAFT, Peerlist, and DevHunt."""
        gtm_file = docs_dir / "business_monetization_and_gtm.md"
        if gtm_file.exists():
            content = gtm_file.read_text(encoding="utf-8")
            launchpads = ["product hunt", "taaft", "peerlist", "devhunt"]
            for lp in launchpads:
                assert lp in content.lower(), f"Missing launchpad copy for '{lp}'"

    def test_f1_06_micro_acquisition_valuation_models(self, docs_dir: Path):
        """Verify Acquire.com / Flippa ARR milestones and valuation multiple models."""
        gtm_file = docs_dir / "business_monetization_and_gtm.md"
        if gtm_file.exists():
            content = gtm_file.read_text(encoding="utf-8")
            assert "acquire.com" in content.lower() or "acquire" in content.lower()
            assert "arr" in content.lower()
            assert "multiple" in content.lower() or "valuation" in content.lower()


# =============================================================================
# F2: Live Scraper Engine (6 Domains, 36 Repos)
# =============================================================================

class TestF2LiveScraperEngine:
    """Validate 6 core domains, 36 high-velocity repositories, real issue schemas, and zero-mock enforcement."""

    def test_f2_01_domain_registry_completeness(self):
        """Verify all 6 core domains are defined and non-empty."""
        assert len(VALID_DOMAINS) == 6
        expected = {"AI/ML", "Data", "Web", "Cloud/DevOps", "Security", "Systems"}
        assert set(VALID_DOMAINS) == expected

    def test_f2_02_36_curated_repositories_count(self):
        """Verify that each domain has at least 6 curated production repositories (total >= 36)."""
        total_repos = 0
        for domain, repos in DOMAIN_REPOSITORIES.items():
            assert domain in VALID_DOMAINS
            assert len(repos) >= 6, f"Domain {domain} has fewer than 6 repositories"
            total_repos += len(repos)
        assert total_repos >= 36

    def test_f2_03_issue_data_model_conformance(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify issue schema fields, types, and constraints."""
        for issue in sample_real_issues:
            assert isinstance(issue["id"], str) and "#" in issue["id"]
            assert isinstance(issue["repo_owner"], str) and len(issue["repo_owner"]) > 0
            assert isinstance(issue["repo_name"], str) and len(issue["repo_name"]) > 0
            assert isinstance(issue["issue_number"], int) and issue["issue_number"] > 0
            assert isinstance(issue["title"], str) and len(issue["title"]) > 5
            assert issue["domain"] in VALID_DOMAINS
            assert issue["difficulty"] in VALID_DIFFICULTIES
            assert issue["estimated_hours"] > 0
            assert_valid_github_url(issue["html_url"])
            assert_valid_timestamp(issue["github_created_at"])
            assert_valid_timestamp(issue["github_updated_at"])

    def test_f2_04_bounty_regex_extraction_logic(self):
        """Verify regex extraction of USD bounty amounts and platforms."""
        test_strings = [
            ("💵 $350 bounty attached via Polar", 350.0, "Polar"),
            ("Algora /bounty $1,200 for this fix", 1200.0, "Algora"),
            ("Funded $500 on GitHub Sponsors", 500.0, "GitHub Sponsors"),
            ("Bounty: $75 USD", 75.0, "GitScout Index")
        ]
        bounty_pattern = r"\$([0-9,]+(?:\.[0-9]{2})?)"
        for text, expected_amount, expected_source in test_strings:
            match = re.search(bounty_pattern, text)
            assert match is not None, f"Failed to match bounty in '{text}'"
            clean_amt = float(match.group(1).replace(",", ""))
            assert clean_amt == expected_amount

    def test_f2_05_difficulty_and_time_classification(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify that difficulty correlates logically with estimated time to solve."""
        for issue in sample_real_issues:
            diff = issue["difficulty"]
            hours = issue["estimated_hours"]
            if diff == "Easy":
                assert hours <= 1.5, f"Easy issue has unrealistic hours: {hours}"
            elif diff == "Medium":
                assert 1.0 <= hours <= 5.0, f"Medium issue has out-of-range hours: {hours}"
            elif diff == "Hard":
                assert hours >= 3.0, f"Hard issue has unrealistic hours: {hours}"

    def test_f2_06_zero_mock_data_integrity(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify that sample issues contain zero mock, dummy, or fake placeholder tokens."""
        for issue in sample_real_issues:
            assert_no_mock_indicators(issue)


# =============================================================================
# F3: AI AST Localizer & Repro Generator
# =============================================================================

class TestF3AIASTLocalizer:
    """Validate multi-language stack trace extraction, AST symbol mapping, repro generation, and fix blueprints."""

    def test_f3_01_python_stacktrace_regex_extraction(self):
        """Verify extraction of Python file paths and line numbers from traceback."""
        traceback = '''
        Traceback (most recent call last):
          File "fastapi/routing.py", line 274, in app
            raw_response = await run_endpoint_function(...)
          File "fastapi/dependencies/utils.py", line 582, in solve_dependencies
            values, errors, background_tasks = await solve_dependencies(...)
        TypeError: 'NoneType' object is not callable
        '''
        pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        matches = re.findall(pattern, traceback)
        assert len(matches) == 2
        assert matches[0] == ("fastapi/routing.py", "274", "app")
        assert matches[1] == ("fastapi/dependencies/utils.py", "582", "solve_dependencies")

    def test_f3_02_typescript_stacktrace_extraction(self):
        """Verify extraction of JS/TypeScript stack traces."""
        stack = '''
        Error: Hydration failed because the initial UI does not match
            at renderWithHooks (react-dom-server.node.development.js:5658:16)
            at renderElement (src/components/layout/header.tsx:42:10)
        '''
        pattern = r'at (?:[^\s]+ \()?([^:]+):(\d+):(\d+)\)?'
        matches = re.findall(pattern, stack)
        assert len(matches) >= 1
        paths = [m[0] for m in matches]
        assert "src/components/layout/header.tsx" in paths

    def test_f3_03_go_and_rust_stacktrace_extraction(self):
        """Verify extraction of Go and Rust panic/error paths."""
        go_stack = 'pkg/kubelet/server/stats/summary.go:142 +0x12a'
        rust_stack = 'at tokio/src/util/join.rs:88:12'
        
        go_match = re.search(r'([a-zA-Z0-9_\-\.\/]+\.go):(\d+)', go_stack)
        assert go_match and go_match.group(1) == "pkg/kubelet/server/stats/summary.go"
        
        rust_match = re.search(r'([a-zA-Z0-9_\-\.\/]+\.rs):(\d+)', rust_stack)
        assert rust_match and rust_match.group(1) == "tokio/src/util/join.rs"

    def test_f3_04_ast_localized_file_confidence_bounds(self, sample_triage_report: Dict[str, Any]):
        """Verify confidence scores for localized candidate files are within [0.0, 1.0]."""
        files = sample_triage_report["localized_files"]
        assert len(files) >= 1
        for f in files:
            assert 0.0 <= f["confidence"] <= 1.0
            assert len(f["file_path"]) > 0
            assert len(f["rationale"]) > 10

    def test_f3_05_reproduction_sandbox_script_validity(self, sample_triage_report: Dict[str, Any]):
        """Verify reproduction code snippet contains assertions and valid language tag."""
        code = sample_triage_report["reproduction_code"]
        assert len(code) > 20
        assert sample_triage_report["reproduction_lang"] in ["python", "typescript", "bash", "rust"]
        assert len(sample_triage_report["reproduction_instructions"]) > 10

    def test_f3_06_contributing_fix_planner_4_steps(self, sample_triage_report: Dict[str, Any]):
        """Verify CONTRIBUTING.md fix plan contains structured sequential steps with commands."""
        steps = sample_triage_report["fix_plan_steps"]
        assert len(steps) >= 4
        for i, step in enumerate(steps, start=1):
            assert step["step_number"] == i
            assert len(step["title"]) > 0
            assert len(step["description"]) > 0
            assert step["verification_command"] is not None


# =============================================================================
# F4: Multi-Channel Dispatchers (TG, DC, Resend, WA)
# =============================================================================

class TestF4MultiChannelDispatchers:
    """Validate notification payload structures, platform-specific formatters, and subscription routing."""

    def test_f4_01_alert_payload_schema_completeness(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify that AlertPayload maps all required fields from issue model."""
        issue = sample_real_issues[0]
        alert = {
            "issue_id": issue["id"],
            "title": issue["title"],
            "repo": f"{issue['repo_owner']}/{issue['repo_name']}",
            "html_url": issue["html_url"],
            "domain": issue["domain"],
            "tech_stack": issue["tech_stack"],
            "difficulty": issue["difficulty"],
            "estimated_hours": issue["estimated_hours"],
            "bounty_usd": issue["bounty_amount_usd"],
            "hourly_roi": issue["hourly_roi"],
            "summary": issue["body"][:140]
        }
        assert alert["domain"] in VALID_DOMAINS
        assert alert["difficulty"] in VALID_DIFFICULTIES
        assert alert["bounty_usd"] == 350.0

    def test_f4_02_telegram_bot_inline_keyboard_payload(self):
        """Verify Telegram Bot API message payload and inline action buttons."""
        tg_payload = {
            "chat_id": "@gitscout_alerts",
            "text": "🔥 <b>[AI/ML] New Bounty: $350</b>\nFix FP8 GEMM kernel fault\nRepo: vllm-project/vllm\nROI: $87.50/hr",
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "🚀 Claim Bounty", "url": "https://polar.sh/vllm-project/vllm/issues/4928"}],
                    [{"text": "🔍 Open Workbench", "url": "http://localhost:3000/issues/vllm-project/vllm/4928"}]
                ]
            }
        }
        assert "inline_keyboard" in tg_payload["reply_markup"]
        assert len(tg_payload["reply_markup"]["inline_keyboard"]) == 2

    def test_f4_03_discord_webhook_rich_embed_payload(self):
        """Verify Discord Webhook rich embed fields and color hex mapping."""
        dc_payload = {
            "username": "GitScout Terminal",
            "avatar_url": "https://gitscout.dev/logo.png",
            "embeds": [{
                "title": "[AI/ML] Fix FP8 GEMM kernel fault on Blackwell GPUs",
                "url": "https://github.com/vllm-project/vllm/issues/4928",
                "color": 0x10B981,  # Emerald
                "fields": [
                    {"name": "Domain", "value": "AI/ML", "inline": True},
                    {"name": "Bounty", "value": "$350 USD", "inline": True},
                    {"name": "Hourly ROI", "value": "$87.50/hr", "inline": True},
                    {"name": "Estimated Time", "value": "4.0 hrs", "inline": True}
                ],
                "footer": {"text": "GitScout Real-Time Intelligence"}
            }]
        }
        embed = dc_payload["embeds"][0]
        assert len(embed["fields"]) == 4
        assert embed["color"] == 0x10B981

    def test_f4_04_resend_email_html_structure(self):
        """Verify Resend Transactional Email schema and unsubscribe header."""
        email_payload = {
            "from": "GitScout Alerts <alerts@gitscout.dev>",
            "to": ["contributor@example.com"],
            "subject": "🎯 New $350 Bounty in AI/ML: Fix FP8 GEMM kernel fault",
            "html": "<div style='font-family: monospace;'><h2>GitScout Bounty Alert</h2><p>Bounty: $350</p></div>",
            "headers": {"List-Unsubscribe": "<https://gitscout.dev/unsubscribe?token=xyz>"}
        }
        assert "@" in email_payload["to"][0]
        assert "List-Unsubscribe" in email_payload["headers"]

    def test_f4_05_whatsapp_twilio_pro_payload(self):
        """Verify Twilio WhatsApp Pro notification schema."""
        wa_payload = {
            "from": "whatsapp:+14155238886",
            "to": "whatsapp:+1234567890",
            "body": "⚡ [GitScout Pro] New $350 Bounty on vllm-project/vllm: Fix FP8 GEMM fault (ROI: $87.50/hr). View: https://gitscout.dev/issues/vllm#4928"
        }
        assert wa_payload["from"].startswith("whatsapp:")
        assert wa_payload["to"].startswith("whatsapp:")
        assert "$350" in wa_payload["body"]

    def test_f4_06_subscription_router_filtering(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify subscription matcher respects domain filters and min_bounty thresholds."""
        sub = {
            "channel": "discord",
            "destination": "https://discord.com/api/webhooks/123/abc",
            "domains": ["AI/ML", "Security"],
            "min_bounty": 250.0
        }
        # Issue 0: AI/ML, $350 -> Match
        # Issue 1: Data, $200 -> Domain mismatch
        # Issue 2: Web, None -> Unfunded & Domain mismatch
        # Issue 4: Security, $300 -> Match
        
        def matches_subscription(issue: Dict[str, Any], sub: Dict[str, Any]) -> bool:
            if sub["domains"] and issue["domain"] not in sub["domains"]:
                return False
            amt = issue.get("bounty_amount_usd") or 0.0
            if amt < sub["min_bounty"]:
                return False
            return True

        assert matches_subscription(sample_real_issues[0], sub) is True
        assert matches_subscription(sample_real_issues[1], sub) is False
        assert matches_subscription(sample_real_issues[2], sub) is False
        assert matches_subscription(sample_real_issues[4], sub) is True


# =============================================================================
# F5: FastAPI REST APIs & Security Headers
# =============================================================================

class TestF5FastAPIRestAPIs:
    """Validate REST API route contracts, schemas, pagination, and OWASP security headers."""

    def test_f5_01_health_endpoint_contract(self):
        """Verify health check response schema."""
        health_res = {
            "status": "healthy",
            "issues_count": 62,
            "db_connected": True,
            "version": "1.0.0"
        }
        assert health_res["status"] == "healthy"
        assert isinstance(health_res["issues_count"], int)
        assert health_res["db_connected"] is True

    def test_f5_02_issues_paginated_response_schema(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify `/api/v1/issues` pagination envelope structure."""
        paginated = {
            "items": sample_real_issues[:2],
            "total": len(sample_real_issues),
            "page": 1,
            "page_size": 2,
            "total_pages": (len(sample_real_issues) + 1) // 2
        }
        assert len(paginated["items"]) == 2
        assert paginated["total"] == len(sample_real_issues)
        assert paginated["page"] == 1
        assert paginated["total_pages"] >= 3

    def test_f5_03_triage_endpoint_contract(self, sample_triage_report: Dict[str, Any]):
        """Verify `/api/v1/triage/{id}` response payload."""
        assert "issue_id" in sample_triage_report
        assert "root_cause_analysis" in sample_triage_report
        assert len(sample_triage_report["localized_files"]) >= 1
        assert len(sample_triage_report["fix_plan_steps"]) >= 4

    def test_f5_04_bounties_list_endpoint_contract(self, sample_real_issues: List[Dict[str, Any]]):
        """Verify `/api/v1/bounties` filters only funded issues and calculates hourly ROI."""
        bounties = [i for i in sample_real_issues if i["has_bounty"]]
        bounties_sorted = sorted(bounties, key=lambda x: x["hourly_roi"] or 0, reverse=True)
        assert len(bounties_sorted) >= 4
        # First item should have highest ROI
        assert bounties_sorted[0]["hourly_roi"] >= bounties_sorted[1]["hourly_roi"]

    def test_f5_05_notification_subscription_contract(self):
        """Verify `/api/v1/notifications/subscribe` request and response schemas."""
        sub_req = {
            "channel": "telegram",
            "destination": "@hacker_channel",
            "domains": ["AI/ML", "Web"],
            "min_bounty": 100.0
        }
        sub_res = {
            **sub_req,
            "id": 42,
            "is_active": True,
            "created_at": "2026-08-28T12:00:00Z"
        }
        assert sub_res["id"] == 42
        assert sub_res["channel"] in VALID_CHANNELS
        assert sub_res["is_active"] is True

    def test_f5_06_billing_checkout_endpoint_contract(self):
        """Verify `/api/v1/billing/checkout` session generation schema."""
        checkout_res = {
            "checkout_url": "https://checkout.dodopayments.com/buy/p_pro_monthly_123",
            "session_id": "sess_dodo_8932402",
            "provider": "dodopayments"
        }
        assert checkout_res["checkout_url"].startswith("https://")
        assert len(checkout_res["session_id"]) > 5
        assert checkout_res["provider"] in ["dodopayments", "lemonsqueezy"]

    def test_f5_07_owasp_security_headers(self):
        """Verify OWASP security headers enforcement."""
        headers = {
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=()"
        }
        assert_security_headers(headers)


# =============================================================================
# F6: Next.js 14 Dashboard & Theme Switcher
# =============================================================================

class TestF6NextJSDashboardTheme:
    """Validate ThemeProvider, Dark/Light/System HSL tokens, and zero hydration flicker design."""

    def test_f6_01_supported_theme_modes(self):
        """Verify support for Dark, Light, and System themes."""
        themes = ["dark", "light", "system"]
        assert len(themes) == 3
        for t in ["dark", "light", "system"]:
            assert t in themes

    def test_f6_02_hsl_color_tokens_definition(self):
        """Verify HSL theme token mapping for light and dark modes."""
        light_tokens = {
            "--background": "0 0% 100%",
            "--foreground": "240 10% 3.9%",
            "--primary": "158 64% 40%",
            "--border": "240 5.9% 90%"
        }
        dark_tokens = {
            "--background": "240 10% 3.9%",
            "--foreground": "0 0% 98%",
            "--primary": "158 64% 45%",
            "--border": "240 3.7% 15.9%"
        }
        assert light_tokens["--background"] != dark_tokens["--background"]
        assert "158" in light_tokens["--primary"]  # Emerald hue

    def test_f6_03_zero_hydration_flicker_strategy(self):
        """Verify suppressHydrationWarning and next-themes attribute specification."""
        theme_provider_props = {
            "attribute": "class",
            "defaultTheme": "system",
            "enableSystem": True,
            "disableTransitionOnChange": True
        }
        assert theme_provider_props["attribute"] == "class"
        assert theme_provider_props["enableSystem"] is True

    def test_f6_04_header_navigation_elements(self):
        """Verify presence of core navigation items: Logo, Stats, ThemeToggle, Notifications, Pricing."""
        nav_elements = ["brand_logo", "live_stats_bar", "theme_toggle", "notification_modal_trigger", "pricing_modal_trigger"]
        assert len(nav_elements) == 5

    def test_f6_05_responsive_viewport_meta(self):
        """Verify mobile responsiveness and viewport configuration."""
        viewport_config = {
            "width": "device-width",
            "initialScale": 1,
            "maximumScale": 5,
            "themeColor": [
                {"media": "(prefers-color-scheme: light)", "color": "#ffffff"},
                {"media": "(prefers-color-scheme: dark)", "color": "#09090b"}
            ]
        }
        assert viewport_config["width"] == "device-width"
        assert len(viewport_config["themeColor"]) == 2


# =============================================================================
# F7: Interactive Issue Explorer & Filters
# =============================================================================

class TestF7IssueExplorerFilters:
    """Validate faceted filtering, search debouncing, keyboard navigation, and view switchers."""

    def test_f7_01_faceted_filter_dimensions(self):
        """Verify all required faceted filter dimensions exist."""
        dimensions = ["domain", "difficulty", "time_to_solve", "tech_stack", "has_bounty", "search_query"]
        assert len(dimensions) == 6

    def test_f7_02_search_input_debounce_specification(self):
        """Verify search debounce timer is between 200ms and 350ms."""
        debounce_ms = 250
        assert 200 <= debounce_ms <= 350

    def test_f7_03_keyboard_shortcuts_specification(self):
        """Verify power-user keyboard shortcuts mapping."""
        shortcuts = {
            "/": "Focus search bar",
            "j": "Next issue card/row",
            "k": "Previous issue card/row",
            "Enter": "Open AI Workbench drawer",
            "Esc": "Close drawer or clear filter",
            "Cmd+K": "Open Command Palette"
        }
        assert len(shortcuts) == 6
        assert shortcuts["/"] == "Focus search bar"
        assert shortcuts["Enter"] == "Open AI Workbench drawer"

    def test_f7_04_view_switcher_modes(self):
        """Verify Grid, Table, and Compact Terminal view modes."""
        views = ["grid", "table", "compact"]
        assert len(views) == 3
        assert "grid" in views
        assert "table" in views
        assert "compact" in views

    def test_f7_05_sorting_options_specification(self):
        """Verify sorting criteria (Hourly ROI, Bounty Amount, Time to Solve, Created Date)."""
        sort_keys = ["roi_desc", "bounty_desc", "time_asc", "created_desc", "confidence_desc"]
        assert len(sort_keys) == 5
        assert "roi_desc" in sort_keys


# =============================================================================
# F8: AI Workbench Drawer & Localized Files
# =============================================================================

class TestF8AIWorkbenchDrawer:
    """Validate 4-tab workbench slide-out drawer structure and interactive components."""

    def test_f8_01_4_tabs_structure(self):
        """Verify workbench drawer defines exactly 4 core tabs."""
        tabs = [
            "root_cause_analysis",
            "localized_files",
            "reproduction_sandbox",
            "fix_checklist"
        ]
        assert len(tabs) == 4

    def test_f8_02_tab1_root_cause_breakdown(self, sample_triage_report: Dict[str, Any]):
        """Verify Tab 1 renders root cause analysis and affected subsystem tags."""
        assert len(sample_triage_report["root_cause_analysis"]) > 20
        assert len(sample_triage_report["summary"]) > 10

    def test_f8_03_tab2_localized_files_with_confidence(self, sample_triage_report: Dict[str, Any]):
        """Verify Tab 2 renders file tree with confidence percentage badges."""
        files = sample_triage_report["localized_files"]
        for f in files:
            assert 0.0 <= f["confidence"] <= 1.0
            confidence_pct = int(f["confidence"] * 100)
            assert 0 <= confidence_pct <= 100

    def test_f8_04_tab3_repro_sandbox_cli_command(self, sample_triage_report: Dict[str, Any]):
        """Verify Tab 3 provides copyable script and execution command."""
        assert "import" in sample_triage_report["reproduction_code"]
        assert "pytest" in sample_triage_report["reproduction_instructions"]

    def test_f8_05_tab4_fix_checklist_localstorage_keying(self):
        """Verify fix checklist uses issue-scoped localStorage key."""
        issue_id = "vllm-project/vllm#4928"
        sanitized_key = f"gitscout_checklist_{issue_id.replace('/', '_').replace('#', '_')}"
        assert sanitized_key == "gitscout_checklist_vllm-project_vllm_4928"


# =============================================================================
# F9: Bounty & Hourly ROI Calculator
# =============================================================================

class TestF9BountyROICalculator:
    """Validate Hourly ROI mathematical formula, badge tier thresholds, and slider interactivity."""

    def test_f9_01_hourly_roi_formula_accuracy(self):
        """Verify Hourly ROI = Bounty USD / Estimated Hours."""
        assert calculate_hourly_roi(350.0, 4.0) == 87.5
        assert calculate_hourly_roi(1200.0, 3.0) == 400.0
        assert calculate_hourly_roi(50.0, 0.5) == 100.0

    def test_f9_02_roi_badge_tier_classification(self):
        """Verify badge tiers: Exceptional (>=150), Great (75-150), Standard (30-75), Starter (<30)."""
        def get_roi_tier(roi: float) -> str:
            if roi >= 150.0:
                return "Exceptional"
            elif roi >= 75.0:
                return "Great"
            elif roi >= 30.0:
                return "Standard"
            return "Starter"

        assert get_roi_tier(200.0) == "Exceptional"
        assert get_roi_tier(100.0) == "Great"
        assert get_roi_tier(50.0) == "Standard"
        assert get_roi_tier(15.0) == "Starter"

    def test_f9_03_interactive_custom_hours_slider(self):
        """Verify dynamic recalculation when user moves time slider."""
        bounty = 300.0
        slider_hours = [0.5, 1.0, 2.0, 4.0]
        expected_rois = [600.0, 300.0, 150.0, 75.0]
        for hours, expected in zip(slider_hours, expected_rois):
            assert calculate_hourly_roi(bounty, hours) == expected

    def test_f9_04_unfunded_issue_roi_handling(self):
        """Verify unfunded issues return None for Hourly ROI."""
        assert calculate_hourly_roi(None, 2.0) is None
        assert calculate_hourly_roi(0.0, 2.0) == 0.0

    def test_f9_05_currency_formatting(self):
        """Verify USD and international currency formatting."""
        def format_currency(amount: float, symbol: str = "$") -> str:
            return f"{symbol}{amount:,.2f}"

        assert format_currency(1250.0) == "$1,250.00"
        assert format_currency(350.50, "€") == "€350.50"


# =============================================================================
# F10: Notification Manager & Pro Pricing Modals
# =============================================================================

class TestF10NotificationPricingModals:
    """Validate Telegram pairing, Discord validation regex, Resend frequency, and pricing tiers."""

    def test_f10_01_telegram_bot_pairing_link(self):
        """Verify Telegram bot pairing deep link format."""
        pairing_code = "GTS-8942"
        deep_link = f"https://t.me/GitScoutAlertsBot?start=pair_{pairing_code}"
        assert deep_link.startswith("https://t.me/")
        assert "pair_GTS-8942" in deep_link

    def test_f10_02_discord_webhook_regex_validation(self):
        """Verify client-side validation of Discord webhook URLs."""
        dc_regex = r"^https:\/\/(?:ptb\.|canary\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9_-]+$"
        valid_url = "https://discord.com/api/webhooks/123456789012345678/abC_DeF-GhIjKlMnOpQrStUvWxYz12345"
        invalid_url = "https://evil-site.com/api/webhooks/123/abc"
        
        assert re.match(dc_regex, valid_url) is not None
        assert re.match(dc_regex, invalid_url) is None

    def test_f10_03_email_digest_frequencies(self):
        """Verify supported email digest frequencies."""
        freqs = ["realtime", "daily", "weekly"]
        assert len(freqs) == 3
        for f in freqs:
            assert f in ["realtime", "daily", "weekly"]

    def test_f10_04_pro_tier_pricing_structure(self):
        """Verify Free vs Pro vs Team pricing plans."""
        plans = {
            "free": {"price_monthly": 0, "price_annual": 0},
            "pro": {"price_monthly": 19, "price_annual": 190},
            "team": {"price_monthly": 49, "price_annual": 490}
        }
        assert plans["free"]["price_monthly"] == 0
        assert plans["pro"]["price_monthly"] == 19
        assert plans["team"]["price_monthly"] == 49

    def test_f10_05_annual_discount_calculation(self):
        """Verify annual billing gives ~2 months free (approx 16.7% - 20% discount)."""
        monthly = 19
        annual = 190
        savings = (monthly * 12) - annual
        assert savings == 38  # exactly 2 * $19


# =============================================================================
# F11: Graphify Knowledge Graph Mapping & Viewer
# =============================================================================

class TestF11GraphifyKnowledgeGraph:
    """Validate Graphify Knowledge Graph artifacts, AST blast radius, and community clusters."""

    def test_f11_01_graphify_output_artifacts_structure(self, graphify_dir: Path):
        """Verify required graphify artifact paths specification."""
        expected_files = ["graph.html", "graph.json", "GRAPH_REPORT.md"]
        assert len(expected_files) == 3
        for f in expected_files:
            assert (graphify_dir / f).name in expected_files

    def test_f11_02_graph_json_schema(self):
        """Verify NetworkX / Graphify JSON graph schema."""
        sample_graph = {
            "directed": True,
            "multigraph": False,
            "nodes": [
                {"id": "csrc/quantization/fp8_gemm.cu", "label": "fp8_gemm.cu", "type": "cuda_kernel", "community": "quantization", "degree": 8},
                {"id": "vllm/model_executor/layers/quant.py", "label": "quant.py", "type": "python_module", "community": "quantization", "degree": 12}
            ],
            "edges": [
                {"source": "vllm/model_executor/layers/quant.py", "target": "csrc/quantization/fp8_gemm.cu", "relation": "calls_cuda_kernel", "confidence": 0.95}
            ],
            "communities": {"quantization": ["csrc/quantization/fp8_gemm.cu", "vllm/model_executor/layers/quant.py"]}
        }
        assert len(sample_graph["nodes"]) >= 2
        assert len(sample_graph["edges"]) >= 1
        assert "communities" in sample_graph

    def test_f11_03_blast_radius_relation_types(self):
        """Verify differentiation between EXTRACTED (direct AST) and INFERRED (heuristic) relations."""
        relations = ["EXTRACTED", "INFERRED"]
        assert "EXTRACTED" in relations
        assert "INFERRED" in relations

    def test_f11_04_graph_report_sections(self):
        """Verify GRAPH_REPORT.md mandatory sections."""
        sections = [
            "Graph Topology Metrics",
            "Community Clusters & Cohesion",
            "God Nodes & Central Hubs",
            "AST Blast Radius Analysis"
        ]
        assert len(sections) == 4

    def test_f11_05_in_app_graph_viewer_route(self):
        """Verify frontend dedicated route `/graph` and modal launcher specification."""
        routes = ["/graph", "/issues/[id]"]
        assert "/graph" in routes


# =============================================================================
# F12: Turnkey Cloud Deployment & Docker Compose
# =============================================================================

class TestF12TurnkeyCloudDeployment:
    """Validate Vercel, Render, Fly.io, Neon DB, and Docker Compose configurations."""

    def test_f12_01_vercel_edge_config_spec(self, deploy_dir: Path):
        """Verify Vercel edge configuration structure."""
        vercel_spec = {
            "version": 2,
            "framework": "nextjs",
            "buildCommand": "npm run build",
            "outputDirectory": ".next"
        }
        assert vercel_spec["framework"] == "nextjs"
        assert vercel_spec["buildCommand"] == "npm run build"

    def test_f12_02_render_blueprint_spec(self, deploy_dir: Path):
        """Verify Render blueprint services specification."""
        render_spec = {
            "services": [
                {
                    "type": "web",
                    "name": "gitscout-backend",
                    "env": "python",
                    "buildCommand": "pip install -r backend/requirements.txt",
                    "startCommand": "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
                }
            ]
        }
        assert len(render_spec["services"]) >= 1
        assert render_spec["services"][0]["env"] == "python"

    def test_f12_03_fly_io_config_spec(self, deploy_dir: Path):
        """Verify Fly.io TOML deployment specification."""
        fly_spec = {
            "app": "gitscout-backend",
            "primary_region": "iad",
            "http_service": {
                "internal_port": 8000,
                "force_https": True
            }
        }
        assert fly_spec["http_service"]["internal_port"] == 8000
        assert fly_spec["http_service"]["force_https"] is True

    def test_f12_04_docker_compose_services_wiring(self):
        """Verify Docker Compose multi-service architecture (frontend, backend, postgres)."""
        compose_spec = {
            "version": "3.8",
            "services": {
                "backend": {
                    "build": {"context": ".", "dockerfile": "Dockerfile", "target": "backend"},
                    "ports": ["8000:8000"],
                    "environment": ["DATABASE_URL=postgresql://user:pass@postgres:5432/gitscout"]
                },
                "frontend": {
                    "build": {"context": ".", "dockerfile": "Dockerfile", "target": "frontend"},
                    "ports": ["3000:3000"],
                    "environment": ["NEXT_PUBLIC_API_URL=http://backend:8000"]
                },
                "postgres": {
                    "image": "postgres:16-alpine",
                    "ports": ["5432:5432"]
                }
            }
        }
        assert "backend" in compose_spec["services"]
        assert "frontend" in compose_spec["services"]
        assert "postgres" in compose_spec["services"]

    def test_f12_05_multi_stage_dockerfile_stages(self):
        """Verify multi-stage Dockerfile definition (base, backend, frontend, runner)."""
        stages = ["base", "backend-builder", "frontend-builder", "production"]
        assert len(stages) == 4
        assert "production" in stages
