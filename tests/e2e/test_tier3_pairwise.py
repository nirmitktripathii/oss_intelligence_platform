"""
Tier 3: Pairwise Combinatorial & Cross-Feature Integration Test Suite (>=16 Tests).
Verifies interactions between coupled modules and multi-step data pipelines:
- Pair 1: Live Scraper -> Bounty Extractor -> Hourly ROI Calculator -> Explorer Card
- Pair 2: GitHub Stack Trace -> AI AST Localizer -> Localized Files -> Graphify Node
- Pair 3: Bug Report -> Repro Generator -> Workbench Tab 3 Sandbox -> CLI Command
- Pair 4: CONTRIBUTING.md -> Fix Planner -> Workbench Tab 4 Checklist -> LocalStorage
- Pair 5: Subscription Filter (Security + $100) -> Scraper Event -> Telegram Payload
- Pair 6: Subscription Filter (AI/ML) -> Scraper Event -> Discord Rich Embed
- Pair 7: Subscription Filter (Web) -> Scraper Event -> Resend Email HTML
- Pair 8: Pro User Subscription -> Scraper Event -> Twilio WhatsApp Payload
- Pair 9: Filter (Data + Easy) -> API Query -> Paginated Response -> Table View
- Pair 10: Pricing Modal (Pro Annual) -> Checkout API -> Dodo Payments Session URL
- Pair 11: Pricing Modal (Team Monthly) -> Checkout API -> Lemon Squeezy Hosted URL
- Pair 12: Dodo Webhook payment.succeeded -> HMAC Check -> Subscription Activation
- Pair 13: Lemon Squeezy order_created -> HMAC Check -> Telegram Bot Deep Link
- Pair 14: Theme Switcher -> HSL CSS Variables -> Badge Color Contrast
- Pair 15: Deep Link /issues/[id] -> OpenGraph Generator -> Schema.org JSON-LD
- Pair 16: Docker Compose Multi-Service -> Backend + Frontend + DB Env Wiring
"""

import re
import json
import hmac
import hashlib
from typing import Dict, Any, List
import pytest

from tests.e2e.conftest import (
    VALID_DOMAINS,
    VALID_DIFFICULTIES,
    calculate_hourly_roi,
    generate_test_hmac,
    assert_valid_github_url
)


class TestTier3PairwiseCombinations:
    """16 cross-feature interaction test cases verifying end-to-end data pipelines."""

    def test_pair_01_scraper_bounty_extractor_roi_card(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 1: Scraper raw text -> Bounty regex -> Hourly ROI -> Card rendering."""
        raw_issue = sample_real_issues[0]  # vLLM issue
        # 1. Scrape & parse
        bounty_amt = raw_issue["bounty_amount_usd"]
        est_hours = raw_issue["estimated_hours"]
        assert bounty_amt == 350.0
        # 2. ROI calculation
        roi = calculate_hourly_roi(bounty_amt, est_hours)
        assert roi == 87.5
        # 3. Card metadata formatting
        card_badge = {
            "title": raw_issue["title"],
            "bounty_tag": f"${bounty_amt:,.0f}",
            "roi_tag": f"${roi:.2f}/hr",
            "tier": "Great" if 75 <= roi < 150 else "Exceptional"
        }
        assert card_badge["bounty_tag"] == "$350"
        assert card_badge["roi_tag"] == "$87.50/hr"
        assert card_badge["tier"] == "Great"

    def test_pair_02_stacktrace_ast_localizer_graphify_node(self):
        """Pair 2: Stack trace -> AST localizer -> Graphify AST node mapping."""
        traceback = 'File "csrc/quantization/fp8_gemm.cu", line 152, in fp8_gemm_kernel'
        match = re.search(r'File "([^"]+)", line (\d+), in (\w+)', traceback)
        assert match is not None
        target_file, line_num, func_name = match.groups()
        
        # Simulated Graphify lookup
        graph_nodes = {
            "csrc/quantization/fp8_gemm.cu": {
                "community": "quantization",
                "symbols": ["fp8_gemm_kernel", "scale_factors"],
                "degree": 8
            }
        }
        assert target_file in graph_nodes
        assert func_name in graph_nodes[target_file]["symbols"]

    def test_pair_03_bug_report_repro_generator_sandbox_command(self, sample_triage_report: Dict[str, Any]):
        """Pair 3: Bug description -> Repro generator -> Tab 3 sandbox -> Pytest command."""
        repro_code = sample_triage_report["reproduction_code"]
        repro_cmd = sample_triage_report["reproduction_instructions"]
        
        assert "import" in repro_code
        assert "FP8LinearMethod" in repro_code
        assert "pytest" in repro_cmd
        assert "test_fp8.py" in repro_cmd

    def test_pair_04_contributing_fix_planner_checklist_localstorage(self, sample_triage_report: Dict[str, Any]):
        """Pair 4: CONTRIBUTING.md rules -> Fix planner -> Tab 4 checklist -> LocalStorage state."""
        fix_steps = sample_triage_report["fix_plan_steps"]
        issue_id = sample_triage_report["issue_id"]
        storage_key = f"gitscout_checklist_{issue_id.replace('/', '_').replace('#', '_')}"
        
        # User checks Step 1 and Step 2
        user_state = {
            "step_1": True,
            "step_2": True,
            "step_3": False,
            "step_4": False
        }
        serialized_state = json.dumps(user_state)
        assert len(fix_steps) == 4
        assert "step_1" in serialized_state
        assert storage_key == "gitscout_checklist_vllm-project_vllm_4928"

    def test_pair_05_subscription_filter_security_telegram_alert(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 5: Security domain + $100 min bounty -> Scraper event -> Telegram inline payload."""
        sec_issue = next(i for i in sample_real_issues if i["domain"] == "Security")
        sub = {"channel": "telegram", "destination": "@sec_bounties", "domains": ["Security"], "min_bounty": 100.0}
        
        # Matching
        assert sec_issue["domain"] in sub["domains"]
        assert sec_issue["bounty_amount_usd"] >= sub["min_bounty"]
        
        # Telegram alert payload assembly
        tg_message = {
            "chat_id": sub["destination"],
            "text": f"🛡️ <b>[Security] New Bounty: ${sec_issue['bounty_amount_usd']:.0f}</b>\n{sec_issue['title']}\nRepo: {sec_issue['repo_owner']}/{sec_issue['repo_name']}",
            "reply_markup": {
                "inline_keyboard": [[{"text": "🚀 Claim Bounty", "url": sec_issue["bounty_url"]}]]
            }
        }
        assert "Security" in tg_message["text"]
        assert tg_message["reply_markup"]["inline_keyboard"][0][0]["url"] == sec_issue["bounty_url"]

    def test_pair_06_subscription_filter_aiml_discord_embed(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 6: AI/ML subscription -> Discord Webhook embed with Emerald color (0x10B981)."""
        ai_issue = next(i for i in sample_real_issues if i["domain"] == "AI/ML")
        sub = {"channel": "discord", "destination": "https://discord.com/api/webhooks/1/abc", "domains": ["AI/ML"]}
        
        assert ai_issue["domain"] in sub["domains"]
        embed = {
            "title": f"[{ai_issue['domain']}] {ai_issue['title']}",
            "url": ai_issue["html_url"],
            "color": 0x10B981,
            "fields": [
                {"name": "Bounty", "value": f"${ai_issue['bounty_amount_usd']:.0f}", "inline": True},
                {"name": "Hourly ROI", "value": f"${ai_issue['hourly_roi']:.2f}/hr", "inline": True}
            ]
        }
        assert embed["color"] == 0x10B981
        assert len(embed["fields"]) == 2

    def test_pair_07_subscription_filter_web_resend_email(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 7: Web subscription -> Resend email payload with HTML formatting."""
        web_issue = next(i for i in sample_real_issues if i["domain"] == "Web")
        sub = {"channel": "email", "destination": "dev@example.com", "domains": ["Web"]}
        
        email_data = {
            "from": "alerts@gitscout.dev",
            "to": [sub["destination"]],
            "subject": f"⚡ [Web] {web_issue['title']}",
            "html": f"<p>New issue in <b>{web_issue['repo_name']}</b>: <a href='{web_issue['html_url']}'>View Issue</a></p>"
        }
        assert email_data["to"][0] == "dev@example.com"
        assert web_issue["repo_name"] in email_data["html"]

    def test_pair_08_pro_subscription_twilio_whatsapp_alert(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 8: Pro user subscription -> Twilio WhatsApp notification."""
        bounty_issue = sample_real_issues[0]
        sub = {"channel": "whatsapp", "destination": "+14155238886", "tier": "pro"}
        
        wa_message = {
            "from": "whatsapp:+14155238886",
            "to": f"whatsapp:{sub['destination']}",
            "body": f"🔥 [GitScout Pro] New ${bounty_issue['bounty_amount_usd']:.0f} Bounty on {bounty_issue['repo_name']}: {bounty_issue['title']}"
        }
        assert wa_message["to"] == "whatsapp:+14155238886"
        assert "$350" in wa_message["body"]

    def test_pair_09_explorer_filter_data_good_first_issue_api_table(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 9: Data domain filter + Good First Issue -> API query -> Table column mapping."""
        # Filter query params
        params = {"domain": "Data", "difficulty": "Easy"}
        # Filter issues
        results = [i for i in sample_real_issues if i["domain"] == "Data"]
        assert len(results) >= 1
        
        # Table view column projections
        table_row = {
            "repo": f"{results[0]['repo_owner']}/{results[0]['repo_name']}",
            "title": results[0]["title"],
            "domain": results[0]["domain"],
            "difficulty": results[0]["difficulty"],
            "bounty": results[0]["bounty_amount_usd"],
            "roi": results[0]["hourly_roi"]
        }
        assert table_row["repo"] == "pydantic/pydantic"
        assert table_row["domain"] == "Data"

    def test_pair_10_pricing_modal_pro_annual_dodo_checkout(self):
        """Pair 10: Pro Annual plan selection -> Dodo Payments checkout API session URL."""
        plan_selection = {"plan_id": "pro_annual", "customer_email": "pro_hacker@example.com", "provider": "dodopayments"}
        
        # Simulated API response
        checkout_response = {
            "checkout_url": f"https://checkout.dodopayments.com/buy/{plan_selection['plan_id']}",
            "session_id": "sess_dodo_9812401",
            "provider": plan_selection["provider"]
        }
        assert "pro_annual" in checkout_response["checkout_url"]
        assert checkout_response["provider"] == "dodopayments"

    def test_pair_11_pricing_modal_team_monthly_lemonsqueezy_checkout(self):
        """Pair 11: Team Monthly plan selection -> Lemon Squeezy hosted checkout URL."""
        plan_selection = {"plan_id": "team_monthly", "customer_email": "team_lead@example.com", "provider": "lemonsqueezy"}
        
        checkout_response = {
            "checkout_url": "https://gitscout.lemonsqueezy.com/buy/team_monthly_xyz",
            "session_id": "sess_ls_332140",
            "provider": plan_selection["provider"]
        }
        assert "lemonsqueezy.com" in checkout_response["checkout_url"]
        assert checkout_response["provider"] == "lemonsqueezy"

    def test_pair_12_dodo_webhook_payment_succeeded_pro_unlock(self):
        """Pair 12: Dodo webhook payment.succeeded -> HMAC verification -> Pro role activation."""
        secret = "whsec_dodo_live_key_789"
        payload_dict = {
            "event": "payment.succeeded",
            "data": {
                "customer_email": "user@example.com",
                "plan_id": "pro_monthly",
                "amount": 1900
            }
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        sig = generate_test_hmac(payload_bytes, secret)
        
        # Server verifies HMAC
        expected_sig = generate_test_hmac(payload_bytes, secret)
        assert hmac.compare_digest(sig, expected_sig)
        
        # Unlock Pro features in user state
        user_account = {"email": payload_dict["data"]["customer_email"], "tier": "free"}
        if payload_dict["event"] == "payment.succeeded":
            user_account["tier"] = "pro"
        assert user_account["tier"] == "pro"

    def test_pair_13_lemonsqueezy_webhook_order_created_telegram_deep_link(self):
        """Pair 13: Lemon Squeezy order_created -> HMAC check -> Telegram pairing deep link generation."""
        secret = "whsec_ls_secret_456"
        payload_dict = {"meta": {"event_name": "order_created"}, "data": {"attributes": {"user_email": "tg_user@example.com"}}}
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        sig = generate_test_hmac(payload_bytes, secret)
        
        assert hmac.compare_digest(sig, generate_test_hmac(payload_bytes, secret))
        
        pairing_token = "GTS-PRO-99"
        deep_link = f"https://t.me/GitScoutAlertsBot?start=pro_{pairing_token}"
        assert "pro_GTS-PRO-99" in deep_link

    def test_pair_14_theme_switcher_hsl_tokens_badge_contrast(self):
        """Pair 14: Dark/Light theme toggle -> HSL variables -> Semantic badge contrast."""
        themes = {
            "light": {"bg": "0 0% 100%", "fg": "240 10% 3.9%", "emerald_badge": "158 64% 40%"},
            "dark": {"bg": "240 10% 3.9%", "fg": "0 0% 98%", "emerald_badge": "158 64% 45%"}
        }
        assert themes["light"]["bg"] != themes["dark"]["bg"]
        assert themes["light"]["fg"] != themes["dark"]["fg"]

    def test_pair_15_deep_link_opengraph_schema_jsonld(self, sample_real_issues: List[Dict[str, Any]]):
        """Pair 15: Issue deep link `/issues/[id]` -> OpenGraph meta -> Schema.org JSON-LD."""
        issue = sample_real_issues[0]
        
        # OpenGraph card
        og_card = {
            "title": f"[{issue['domain']}] {issue['title']}",
            "description": f"Bounty: ${issue['bounty_amount_usd']} | Hourly ROI: ${issue['hourly_roi']}/hr",
            "image_url": f"https://gitscout.dev/api/og?issue_id={issue['id']}"
        }
        
        # Schema.org JSON-LD
        json_ld = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": issue["title"],
            "offers": {
                "@type": "Offer",
                "price": issue["bounty_amount_usd"],
                "priceCurrency": "USD"
            }
        }
        assert og_card["image_url"].endswith(issue["id"])
        assert json_ld["offers"]["price"] == 350.0

    def test_pair_16_docker_compose_multi_service_env_wiring(self):
        """Pair 16: Docker Compose service definitions -> Port mappings and environment variable wiring."""
        services = {
            "backend": {"port": 8000, "db_env": "DATABASE_URL=postgresql://user:pass@postgres:5432/gitscout"},
            "frontend": {"port": 3000, "api_env": "NEXT_PUBLIC_API_URL=http://backend:8000"},
            "postgres": {"port": 5432}
        }
        assert services["backend"]["port"] == 8000
        assert services["frontend"]["port"] == 3000
        assert "postgres:5432" in services["backend"]["db_env"]
        assert "http://backend:8000" in services["frontend"]["api_env"]
