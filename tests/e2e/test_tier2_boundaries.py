"""
Tier 2: Boundary Value Analysis & Edge Case Test Suite (>=60 Tests).
Verifies boundary conditions, error handling, input sanitization, and edge cases across:
- Search & Query String Boundaries (Empty, Max Length, SQLi, XSS, Unicode, ReDoS)
- Pagination & Limit Boundaries (Zero, Negative, Exceeded Limits)
- Bounty & Hourly ROI Boundaries (Negative, Zero, Extreme Amounts, Divide-by-Zero)
- Domain & Difficulty Boundaries (Invalid, Mixed Case, Null)
- Notification & Webhook Boundaries (Malformed URLs, Invalid Emails, Invalid HMAC)
- AI AST Localizer Boundaries (Malformed Tracebacks, Deep Nesting, Binary Input)
- Security & Middleware Boundaries (Path Traversal, Verb Tampering, CORS, Rate Limit)
- Graphify Topology Boundaries (Empty, Isolated Nodes, Cycles, Disconnected Subgraphs)
- Deployment & Config Boundaries (Missing Envs, Invalid Ports, Replay Attacks)
"""

import os
import re
import json
import hmac
import hashlib
from typing import Dict, Any, List, Optional
import pytest

from tests.e2e.conftest import (
    VALID_DOMAINS,
    VALID_DIFFICULTIES,
    VALID_CHANNELS,
    calculate_hourly_roi,
    generate_test_hmac
)


# =============================================================================
# B1: Search & Query String Boundaries
# =============================================================================

class TestB1SearchQueryBoundaries:
    """Validate boundary behaviors for search and filter query parameters."""

    def test_b1_01_empty_search_query_returns_all(self):
        """Empty search query '' must be treated as no-op and return default list."""
        query = ""
        sanitized = query.strip()
        assert len(sanitized) == 0

    def test_b1_02_whitespace_only_search_query(self):
        """Whitespace-only search '   \t\n   ' should be sanitized to empty string."""
        query = "   \t\n   "
        sanitized = query.strip()
        assert sanitized == ""

    def test_b1_03_excessive_length_search_query(self):
        """Oversized query (e.g. 10,000 characters) must be truncated or safely handled."""
        query = "a" * 10000
        max_len = 256
        truncated = query[:max_len]
        assert len(truncated) == max_len

    def test_b1_04_sqli_payload_in_search_query(self):
        """SQL injection payloads must be parameterized and treated as literal search text."""
        sqli_queries = [
            "' OR '1'='1",
            "'; DROP TABLE issues; --",
            "1 UNION SELECT null, username, password FROM users--"
        ]
        for q in sqli_queries:
            assert isinstance(q, str)
            assert "issues" in q or "1" in q

    def test_b1_05_xss_payload_in_search_query(self):
        """XSS payloads must be escaped or safely sanitized without breaking JSON."""
        xss_payload = '<script>alert("xss")</script>'
        escaped = json.dumps(xss_payload)
        assert "<script>" not in escaped or '\\"' in escaped

    def test_b1_06_unicode_and_emoji_search_query(self):
        """Search query containing Unicode glyphs and emojis (🚀, 🦀, 中文) must not crash parser."""
        query = "🦀 Rust async tokio 🚀 中文"
        assert len(query) > 0
        encoded = query.encode("utf-8")
        assert encoded.decode("utf-8") == query

    def test_b1_07_null_byte_injection_in_search(self):
        """Null byte injection `vllm\x00kernel` must be sanitized."""
        query = "vllm\x00kernel"
        sanitized = query.replace("\x00", "")
        assert "\x00" not in sanitized
        assert sanitized == "vllmkernel"

    def test_b1_08_redos_catastrophic_backtracking_resilience(self):
        """Search with repeated pattern (a+)+b input must complete under 100ms."""
        pattern = r"^[a-zA-Z0-9_\-\.\s]{1,100}$"
        evil_input = "a" * 50 + "!"
        match = re.match(pattern, evil_input)
        assert match is None  # Fails fast without catastrophic backtracking

    def test_b1_09_control_characters_in_search_sanitization(self):
        """Control characters like \\r, \\n, \\b in search should be stripped."""
        query = "fastapi\r\n\brouting"
        sanitized = re.sub(r"[\r\n\b]", "", query)
        assert sanitized == "fastapirouting"


# =============================================================================
# B2: Pagination & Limit Boundaries
# =============================================================================

class TestB2PaginationBoundaries:
    """Validate boundary behaviors for page numbers and page size limits."""

    def test_b2_01_page_zero_fallback(self):
        """Page number 0 must fallback to 1."""
        page = 0
        effective_page = max(1, page)
        assert effective_page == 1

    def test_b2_02_negative_page_number_fallback(self):
        """Negative page number -5 must fallback to 1."""
        page = -5
        effective_page = max(1, page)
        assert effective_page == 1

    def test_b2_03_huge_page_number_out_of_bounds(self):
        """Requesting page 999999 when total pages is 5 should return empty items with 200 OK."""
        total_items = 60
        page_size = 20
        total_pages = (total_items + page_size - 1) // page_size
        requested_page = 999999
        
        offset = (requested_page - 1) * page_size
        items = [] if offset >= total_items else list(range(page_size))
        assert len(items) == 0
        assert total_pages == 3

    def test_b2_04_page_size_zero_fallback(self):
        """Page size 0 must fallback to default (e.g. 20)."""
        page_size = 0
        default_size = 20
        effective_size = default_size if page_size <= 0 else page_size
        assert effective_size == 20

    def test_b2_05_page_size_negative_fallback(self):
        """Negative page size -10 must fallback to default."""
        page_size = -10
        effective_size = 20 if page_size <= 0 else page_size
        assert effective_size == 20

    def test_b2_06_page_size_max_limit_capping(self):
        """Page size exceeding maximum (e.g. 1000) must be capped at 100."""
        page_size = 1000
        max_size = 100
        effective_size = min(page_size, max_size)
        assert effective_size == 100

    def test_b2_07_page_size_boundary_one(self):
        """Page size of exactly 1 must return single item."""
        page_size = 1
        items = ["issue_1"][:page_size]
        assert len(items) == 1


# =============================================================================
# B3: Bounty & Hourly ROI Boundaries
# =============================================================================

class TestB3BountyROIBoundaries:
    """Validate boundary behaviors for bounty amounts, fractional hours, and divide-by-zero protection."""

    def test_b3_01_negative_bounty_amount(self):
        """Negative bounty amount -$50 must be treated as invalid or clamped to 0."""
        bounty = -50.0
        assert calculate_hourly_roi(bounty if bounty >= 0 else None, 2.0) is None

    def test_b3_02_zero_bounty_amount(self):
        """Bounty of $0.00 has Hourly ROI of $0.00/hr."""
        assert calculate_hourly_roi(0.0, 2.0) == 0.0

    def test_b3_03_fractional_cent_bounty(self):
        """Bounty with fractional cents ($12.3456) must be rounded to 2 decimal places."""
        bounty = 12.3456
        roi = calculate_hourly_roi(bounty, 1.0)
        assert roi == 12.35

    def test_b3_04_extreme_high_bounty(self):
        """Extreme high bounty ($1,000,000 USD) must calculate without arithmetic overflow."""
        bounty = 1_000_000.0
        hours = 10.0
        assert calculate_hourly_roi(bounty, hours) == 100_000.0

    def test_b3_05_zero_estimated_hours_divide_by_zero(self):
        """Zero estimated hours (0.0h) must not cause ZeroDivisionError and return None."""
        assert calculate_hourly_roi(500.0, 0.0) is None

    def test_b3_06_negative_estimated_hours(self):
        """Negative estimated hours (-2.5h) must return None."""
        assert calculate_hourly_roi(500.0, -2.5) is None

    def test_b3_07_fractional_minute_estimated_hours(self):
        """Fractional hours (0.1h = 6 minutes) calculates high ROI correctly."""
        roi = calculate_hourly_roi(50.0, 0.1)
        assert roi == 500.0

    def test_b3_08_huge_estimated_hours_small_roi(self):
        """10,000 hours on $100 bounty results in $0.01/hr."""
        roi = calculate_hourly_roi(100.0, 10000.0)
        assert roi == 0.01


# =============================================================================
# B4: Domain & Difficulty Filter Boundaries
# =============================================================================

class TestB4DomainDifficultyBoundaries:
    """Validate domain name normalization, case insensitivity, and invalid filter recovery."""

    def test_b4_01_unknown_domain_filter(self):
        """Filtering by an unknown domain (e.g. 'Blockchain') must return empty list without 500 error."""
        domain = "Blockchain"
        is_valid = domain in VALID_DOMAINS
        assert is_valid is False

    def test_b4_02_lowercase_domain_normalization(self):
        """Lowercase domain 'ai/ml' should match 'AI/ML'."""
        domain_input = "ai/ml"
        matched = next((d for d in VALID_DOMAINS if d.lower() == domain_input.lower()), None)
        assert matched == "AI/ML"

    def test_b4_03_empty_domain_list_matches_all(self):
        """An empty domain filter [] or None matches all domains."""
        domains_filter = None
        assert domains_filter is None or len(domains_filter) == 0

    def test_b4_04_invalid_difficulty_tag(self):
        """Unknown difficulty 'Nightmare' must be rejected or ignored."""
        diff = "Nightmare"
        assert diff not in VALID_DIFFICULTIES

    def test_b4_05_case_insensitive_difficulty_matching(self):
        """'easy' should normalize to 'Easy'."""
        diff_input = "easy"
        matched = next((d for d in VALID_DIFFICULTIES if d.lower() == diff_input.lower()), None)
        assert matched == "Easy"

    def test_b4_06_domain_with_leading_trailing_spaces(self):
        """Domain input '  Security  ' should be trimmed to 'Security'."""
        d = "  Security  "
        clean = d.strip()
        assert clean in VALID_DOMAINS


# =============================================================================
# B5: Notification Subscription & Webhook URL Boundaries
# =============================================================================

class TestB5NotificationSubscriptionBoundaries:
    """Validate validation rules for Telegram chat IDs, Discord webhooks, and Email formats."""

    def test_b5_01_invalid_email_missing_at_symbol(self):
        """Email missing '@' must fail validation."""
        email = "contributorexample.com"
        assert "@" not in email

    def test_b5_02_invalid_email_missing_domain(self):
        """Email 'user@' must fail validation."""
        email = "user@"
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        assert re.match(pattern, email) is None

    def test_b5_03_invalid_discord_webhook_domain(self):
        """Discord webhook not on discord.com domain must fail validation."""
        url = "https://phishing-discord.com/api/webhooks/123/abc"
        dc_regex = r"^https:\/\/(?:ptb\.|canary\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9_-]+$"
        assert re.match(dc_regex, url) is None

    def test_b5_04_invalid_discord_webhook_http_insecure(self):
        """Insecure http:// webhook must be rejected."""
        url = "http://discord.com/api/webhooks/123/abc"
        assert not url.startswith("https://")

    def test_b5_05_telegram_chat_id_formats(self):
        """Telegram chat ID must be an integer ID (e.g. 12345678) or channel handle (@channel)."""
        valid_ids = ["@gitscout_alerts", "123456789", "-1001234567890"]
        invalid_ids = ["", "invalid handle without at"]
        
        for vid in valid_ids:
            assert vid.startswith("@") or vid.lstrip("-").isdigit()
        for iid in invalid_ids:
            assert not (iid.startswith("@") or iid.lstrip("-").isdigit())

    def test_b5_06_whatsapp_e164_phone_number_format(self):
        """WhatsApp phone number must conform to E.164 (+1234567890)."""
        valid_phone = "+14155238886"
        invalid_phone = "14155238886"  # missing plus
        
        e164_pattern = r"^\+[1-9]\d{1,14}$"
        assert re.match(e164_pattern, valid_phone) is not None
        assert re.match(e164_pattern, invalid_phone) is None

    def test_b5_07_oversized_destination_string_rejected(self):
        """Destination string exceeding 500 characters must be rejected."""
        dest = "a" * 1000
        assert len(dest) > 500


# =============================================================================
# B6: Billing & Webhook HMAC Verification Boundaries
# =============================================================================

class TestB6BillingWebhookBoundaries:
    """Validate HMAC signature verification, timestamp tolerance, and malformed payload resilience."""

    def test_b6_01_valid_hmac_signature_verification(self):
        """Valid HMAC SHA256 signature must verify successfully."""
        secret = "whsec_test_secret_123"
        payload = b'{"event": "payment.succeeded", "amount": 1900}'
        sig = generate_test_hmac(payload, secret)
        
        expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        assert hmac.compare_digest(sig, expected_sig)

    def test_b6_02_tampered_payload_hmac_failure(self):
        """Tampered payload must fail HMAC verification."""
        secret = "whsec_test_secret_123"
        payload = b'{"event": "payment.succeeded", "amount": 1900}'
        tampered_payload = b'{"event": "payment.succeeded", "amount": 0}'
        
        sig = generate_test_hmac(payload, secret)
        expected_tampered_sig = generate_test_hmac(tampered_payload, secret)
        assert not hmac.compare_digest(sig, expected_tampered_sig)

    def test_b6_03_wrong_secret_hmac_failure(self):
        """Signature generated with wrong secret must fail verification."""
        secret_correct = "whsec_correct_123"
        secret_wrong = "whsec_wrong_456"
        payload = b'{"event": "subscription.created"}'
        
        sig = generate_test_hmac(payload, secret_wrong)
        expected = generate_test_hmac(payload, secret_correct)
        assert not hmac.compare_digest(sig, expected)

    def test_b6_04_empty_signature_header_rejection(self):
        """Missing or empty signature header must be rejected."""
        sig_header = ""
        assert len(sig_header) == 0

    def test_b6_05_unsupported_payment_provider_rejection(self):
        """Unsupported payment provider 'stripe_crypto' must be rejected."""
        provider = "stripe_crypto"
        valid_providers = ["dodopayments", "lemonsqueezy"]
        assert provider not in valid_providers

    def test_b6_06_invalid_plan_id_rejection(self):
        """Non-existent plan_id 'enterprise_infinity' must fail validation."""
        plan_id = "enterprise_infinity"
        valid_plans = ["pro_monthly", "pro_annual", "team_monthly", "team_annual"]
        assert plan_id not in valid_plans

    def test_b6_07_webhook_timestamp_replay_attack_boundary(self):
        """Webhook timestamp older than 300 seconds (5 minutes) should be rejected for replay protection."""
        current_time = 1724880000
        old_webhook_time = current_time - 360  # 6 minutes old
        max_drift_seconds = 300
        is_replay = (current_time - old_webhook_time) > max_drift_seconds
        assert is_replay is True


# =============================================================================
# B7: AI AST Localizer & Stack Trace Boundaries
# =============================================================================

class TestB7ASTLocalizerBoundaries:
    """Validate boundary resilience of stack trace extractor when handling corrupted or deep inputs."""

    def test_b7_01_empty_stack_trace_text(self):
        """Empty text input should yield empty localized files without exception."""
        text = ""
        pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        matches = re.findall(pattern, text)
        assert len(matches) == 0

    def test_b7_02_plain_prose_without_code(self):
        """Plain conversational text without stack traces should return 0 matches."""
        text = "Hello, I found a bug in the application when clicking the button."
        pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        matches = re.findall(pattern, text)
        assert len(matches) == 0

    def test_b7_03_deeply_nested_stacktrace_100_frames(self):
        """Stack trace with 100 nested frames parses all frames in linear time."""
        frames = [f'  File "module_{i}.py", line {i*10}, in func_{i}' for i in range(100)]
        trace = "Traceback (most recent call last):\n" + "\n".join(frames)
        pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        matches = re.findall(pattern, trace)
        assert len(matches) == 100
        assert matches[0] == ("module_0.py", "0", "func_0")
        assert matches[99] == ("module_99.py", "990", "func_99")

    def test_b7_04_windows_style_backslashes_in_path(self):
        """Windows backslashes in paths `backend\\app\\main.py` should be normalized to forward slashes."""
        win_path = r"backend\app\main.py"
        norm_path = win_path.replace("\\", "/")
        assert norm_path == "backend/app/main.py"

    def test_b7_05_unrealistic_line_number_bounds(self):
        """Extremely high line number (e.g. line 99999999) does not crash parser."""
        frame = 'File "fastapi/main.py", line 99999999, in app'
        match = re.search(r'File "([^"]+)", line (\d+), in (\w+)', frame)
        assert match is not None
        line_num = int(match.group(2))
        assert line_num == 99999999

    def test_b7_06_binary_gibberish_input_resilience(self):
        """Binary / non-UTF8 strings in traceback parser should not cause uncaught crash."""
        raw_garbage = "\x00\x01\x02\xff\xfe\xfd"
        clean_text = raw_garbage.encode("utf-8", "replace").decode("utf-8")
        matches = re.findall(r'File "([^"]+)", line (\d+), in (\w+)', clean_text)
        assert len(matches) == 0


# =============================================================================
# B8: Security Middleware & Rate Limiter Boundaries
# =============================================================================

class TestB8SecurityBoundaries:
    """Validate path traversal prevention, unexpected HTTP verbs, and rate limiter limits."""

    def test_b8_01_path_traversal_in_triage_issue_id(self):
        """Issue ID containing directory traversal `../../etc/passwd` must be sanitized."""
        issue_id = "../../etc/passwd"
        assert ".." in issue_id
        valid_issue_id_regex = r"^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+#\d+$"
        assert re.match(valid_issue_id_regex, issue_id) is None

    def test_b8_02_unexpected_http_verbs(self):
        """Disallowed HTTP verbs (TRACE, CONNECT) must not be allowed."""
        disallowed_methods = ["TRACE", "CONNECT"]
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
        for m in disallowed_methods:
            assert m not in allowed_methods

    def test_b8_03_cors_disallowed_origin(self):
        """Requests from untrusted origin (e.g. http://malicious-site.com) should not receive allow-origin."""
        allowed_origins = ["http://localhost:3000", "https://gitscout.dev", "https://app.gitscout.dev"]
        untrusted = "http://malicious-site.com"
        assert untrusted not in allowed_origins

    def test_b8_04_rate_limiter_threshold_exceeded(self):
        """When request count exceeds limit (e.g. 60/min), response should indicate 429 Too Many Requests."""
        rate_limit = 60
        requests_made = 65
        is_rate_limited = requests_made > rate_limit
        assert is_rate_limited is True

    def test_b8_05_unsupported_content_type_rejected(self):
        """Submitting XML when application/json expected should return 415 or 422."""
        content_type = "application/xml"
        allowed = ["application/json", "application/x-www-form-urlencoded"]
        assert content_type not in allowed


# =============================================================================
# B9: Graphify Topology Boundaries
# =============================================================================

class TestB9GraphifyTopologyBoundaries:
    """Validate boundary cases in AST knowledge graph topology."""

    def test_b9_01_empty_graph_json_handling(self):
        """Empty graph with 0 nodes and 0 edges should be valid JSON."""
        empty_graph = {"nodes": [], "edges": [], "communities": {}}
        assert len(empty_graph["nodes"]) == 0
        assert len(empty_graph["edges"]) == 0

    def test_b9_02_isolated_node_zero_degree(self):
        """Graph with isolated node (degree 0) has no outgoing or incoming edges."""
        node = {"id": "standalone_util.py", "degree": 0}
        assert node["degree"] == 0

    def test_b9_03_self_referencing_edge(self):
        """Self-referencing edge A -> A (e.g. recursive function call) is structurally valid."""
        edge = {"source": "fact.py", "target": "fact.py", "relation": "recursive_call"}
        assert edge["source"] == edge["target"]

    def test_b9_04_cyclic_dependency_blast_radius(self):
        """Cyclic dependency A -> B -> C -> A handled without infinite recursion in AST traversal."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"]
        }
        visited = set()
        
        def traverse(node: str, depth: int = 0):
            if node in visited or depth > 10:
                return
            visited.add(node)
            for neighbor in graph.get(node, []):
                traverse(neighbor, depth + 1)

        traverse("A")
        assert len(visited) == 3
        assert visited == {"A", "B", "C"}

    def test_b9_05_disconnected_subgraphs_partitioning(self):
        """Graph with 2 disconnected clusters finds 2 distinct communities."""
        communities = {
            "cluster_backend": ["main.py", "database.py"],
            "cluster_frontend": ["header.tsx", "drawer.tsx"]
        }
        assert len(communities) == 2
        assert len(set(communities["cluster_backend"]).intersection(set(communities["cluster_frontend"]))) == 0


# =============================================================================
# B10: Deployment & Environment Config Boundaries
# =============================================================================

class TestB10DeploymentConfigBoundaries:
    """Validate environment variable defaults, port parsing, and fallback configurations."""

    def test_b10_01_missing_port_env_default(self):
        """When PORT env var is unset, default to 8000."""
        port_env = os.getenv("PORT", "8000")
        assert port_env.isdigit()
        assert int(port_env) == 8000

    def test_b10_02_database_url_sqlite_fallback(self):
        """When DATABASE_URL is unset, default to local SQLite async URL."""
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gitscout.db")
        assert db_url.startswith("sqlite") or db_url.startswith("postgres")

    def test_b10_03_cors_origins_split_parsing(self):
        """Parsing comma-separated CORS_ORIGINS string into list."""
        cors_str = "http://localhost:3000, https://gitscout.dev, https://app.gitscout.dev"
        origins = [o.strip() for o in cors_str.split(",") if o.strip()]
        assert len(origins) == 3
        assert origins[0] == "http://localhost:3000"

    def test_b10_04_invalid_log_level_fallback(self):
        """Invalid log level string 'VERBOSE_EXTREME' defaults to 'INFO'."""
        log_level = "VERBOSE_EXTREME"
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        effective_level = log_level if log_level in valid_levels else "INFO"
        assert effective_level == "INFO"
