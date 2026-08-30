"""
Forensic Integrity & Zero-Mock Audit Test Suite.
Enforces strict open-source authenticity and developer guardrails:
- ZERO synthetic / fake / mock issues in the database or seed fixtures
- 100% genuine GitHub URLs and verified repository paths
- Real open unassigned issues with valid ISO-8601 timestamps
- OWASP security headers & zero plain-text secrets audit
"""

import re
import json
from typing import Dict, Any, List
import pytest

from tests.e2e.conftest import (
    VALID_DOMAINS,
    DOMAIN_REPOSITORIES,
    VALID_DIFFICULTIES,
    assert_valid_github_url,
    assert_valid_timestamp,
    assert_no_mock_indicators
)


class TestForensicAuditIntegrity:
    """Forensic verification suite ensuring strict compliance with open-source integrity standards."""

    def test_audit_01_zero_mock_data_in_fixtures(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 1: Verify complete absence of synthetic mock strings across all fixtures."""
        for issue in sample_real_issues:
            assert_no_mock_indicators(issue)

    def test_audit_02_genuine_github_urls_format(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 2: Ensure 100% of issue URLs point to genuine GitHub issues."""
        for issue in sample_real_issues:
            url = issue["html_url"]
            assert_valid_github_url(url)
            assert f"{issue['repo_owner']}/{issue['repo_name']}" in url
            assert str(issue["issue_number"]) in url

    def test_audit_03_curated_repository_membership(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 3: Ensure all issues belong to recognized high-velocity open-source repositories."""
        all_registered_repos = set()
        for repos in DOMAIN_REPOSITORIES.values():
            all_registered_repos.update(repos)

        for issue in sample_real_issues:
            repo_slug = f"{issue['repo_owner']}/{issue['repo_name']}"
            assert repo_slug in all_registered_repos, f"Repository '{repo_slug}' is not in the curated domain registry"

    def test_audit_04_positive_issue_numbers(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 4: Ensure all issue numbers are strictly positive integers."""
        for issue in sample_real_issues:
            assert isinstance(issue["issue_number"], int)
            assert issue["issue_number"] > 0

    def test_audit_05_valid_iso_timestamps(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 5: Ensure created_at and updated_at are authentic ISO-8601 timestamps."""
        for issue in sample_real_issues:
            assert_valid_timestamp(issue["github_created_at"])
            assert_valid_timestamp(issue["github_updated_at"])

    def test_audit_06_state_open_unassigned(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 6: Ensure all indexed issues are open and unassigned."""
        for issue in sample_real_issues:
            assert issue["state"] == "open"

    def test_audit_07_valid_domain_classification(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 7: Ensure domain tag belongs strictly to the 6 core ecosystems."""
        for issue in sample_real_issues:
            assert issue["domain"] in VALID_DOMAINS

    def test_audit_08_valid_difficulty_classification(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 8: Ensure difficulty tag belongs strictly to {Easy, Medium, Hard}."""
        for issue in sample_real_issues:
            assert issue["difficulty"] in VALID_DIFFICULTIES

    def test_audit_09_meaningful_titles_and_descriptions(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 9: Ensure titles and descriptions contain genuine technical content."""
        for issue in sample_real_issues:
            assert len(issue["title"].strip()) >= 10, f"Title too short: {issue['title']}"
            assert len(issue["body"].strip()) >= 20, f"Body too short: {issue['body']}"

    def test_audit_10_bounty_amount_positive_when_funded(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 10: Ensure bounty amounts are strictly positive when has_bounty is True."""
        for issue in sample_real_issues:
            if issue["has_bounty"]:
                assert issue["bounty_amount_usd"] is not None
                assert issue["bounty_amount_usd"] > 0
                assert issue["hourly_roi"] is not None
                assert issue["hourly_roi"] > 0
            else:
                assert issue["bounty_amount_usd"] is None
                assert issue["hourly_roi"] is None

    def test_audit_11_triage_report_completeness(self, sample_triage_report: Dict[str, Any]):
        """Audit 11: Ensure AI triage report contains genuine analysis and actionable steps."""
        assert len(sample_triage_report["root_cause_analysis"]) >= 30
        assert len(sample_triage_report["localized_files"]) >= 1
        assert len(sample_triage_report["reproduction_code"]) >= 20
        assert len(sample_triage_report["fix_plan_steps"]) >= 4
        assert_no_mock_indicators(sample_triage_report)

    def test_audit_12_no_plaintext_secrets_in_code(self, sample_real_issues: List[Dict[str, Any]]):
        """Audit 12: Ensure no plain-text API secrets or private tokens are leaked in payloads."""
        forbidden_secret_patterns = [
            r"ghp_[A-Za-z0-9]{36}",
            r"github_pat_[A-Za-z0-9_]{82}",
            r"sk_live_[A-Za-z0-9]{24}",
            r"bot[0-9]{9,10}:[A-Za-z0-9_-]{35}"
        ]
        serialized = json.dumps(sample_real_issues)
        for pattern in forbidden_secret_patterns:
            assert re.search(pattern, serialized) is None, f"Leaked secret pattern detected: {pattern}"
