"""Unit tests for GitHub Client, Bounty Extractor, Classifier, and Orchestrator."""

import pytest
import respx
import httpx
from app.schemas.issue import IssueDifficulty
from app.scrapers.bounty_extractor import BountyExtractor
from app.scrapers.classifier import IssueClassifier
from app.scrapers.domain_registry import DOMAIN_REGISTRY, get_repo_by_fullname
from app.scrapers.github_client import GitHubClient
from app.scrapers.orchestrator import ScraperOrchestrator


def test_domain_registry_completeness():
    """Verify registry contains 36 repositories across 6 domains."""
    assert len(DOMAIN_REGISTRY) == 36
    domains = set(r.domain for r in DOMAIN_REGISTRY)
    assert len(domains) == 6

    # Verify lookup helper
    repo = get_repo_by_fullname("fastapi/fastapi")
    assert repo.owner == "fastapi"
    assert repo.repo == "fastapi"
    assert repo.primary_language == "Python"


def test_bounty_extractor_regex_and_labels():
    """Test multi-source bounty parsing."""
    # 1. Label with amount
    labels = [{"name": "bounty: $350", "color": "008672"}]
    has_bounty, amount, source, url = BountyExtractor.parse_issue("Fix memory leak", "", labels, "https://github.com/foo/bar/issues/1")
    assert has_bounty is True
    assert amount == 350.0

    # 2. Body with Polar text & URL
    body = "Funding on Polar: $250\nhttps://polar.sh/fastapi/fastapi/issues/100"
    has_bounty, amount, source, url = BountyExtractor.parse_issue("Support OpenAPI 3.1", body, [], "https://github.com/fastapi/fastapi/issues/100")
    assert has_bounty is True
    assert amount == 250.0
    assert source == "Polar"
    assert "polar.sh" in url

    # 3. Algora bot command
    body = "/bounty $500 on this issue"
    has_bounty, amount, source, url = BountyExtractor.parse_issue("Add streaming RPC", body, [], "https://github.com/trpc/trpc/issues/50")
    assert has_bounty is True
    assert amount == 500.0
    assert source == "Algora"

    # 4. Unfunded issue
    has_bounty, amount, source, url = BountyExtractor.parse_issue("Just a typo in docs", "Fixed word", [], "https://github.com/foo/bar/issues/2")
    assert has_bounty is False
    assert amount is None

    # 5. Bounty label present but NO parseable amount -> honest undisclosed amount.
    # Must never fabricate a dollar figure (regression guard against the old
    # hardcoded $100 baseline estimate).
    labels = [{"name": "💰 Bounty", "color": "008672"}]
    has_bounty, amount, source, url = BountyExtractor.parse_issue("Improve error messages", "No amount stated here", labels, "https://github.com/foo/bar/issues/3")
    assert has_bounty is True
    assert amount is None


def test_classifier_difficulty_and_roi():
    """Test difficulty assignment and $/hr ROI calculation."""
    # Easy
    easy_labels = [{"name": "good first issue", "color": "7057ff"}]
    diff = IssueClassifier.classify_difficulty(easy_labels, "Typo in README", "Fix spelling")
    assert diff == IssueDifficulty.EASY
    hours = IssueClassifier.estimate_hours(diff)
    assert hours <= 1.0

    # Hard
    hard_labels = [{"name": "architecture", "color": "d73a4a"}]
    diff_hard = IssueClassifier.classify_difficulty(hard_labels, "RFC: Complete rewrite of executor", "Huge refactor")
    assert diff_hard == IssueDifficulty.HARD
    hours_hard = IssueClassifier.estimate_hours(diff_hard)
    assert hours_hard >= 6.0

    # ROI Calculation
    roi = IssueClassifier.calculate_hourly_roi(bounty_amount_usd=300.0, estimated_hours=2.0)
    assert roi == 150.0


@pytest.mark.asyncio
@respx.mock
async def test_github_client_fetch_issues_and_etag():
    """Verify GitHub client issue fetching, strict verification, and ETag caching."""
    client = GitHubClient(token="fake_token", base_url="https://api.github.com")

    # Mock first response with ETag
    mock_issues = [
        {
            "id": 1,
            "number": 101,
            "title": "Open Unassigned Issue",
            "body": "Description",
            "state": "open",
            "assignee": None,
            "pull_request": None,
            "user": {"login": "dev1"},
            "labels": [{"name": "bug"}],
            "created_at": "2026-08-01T12:00:00Z",
            "updated_at": "2026-08-01T12:00:00Z",
            "html_url": "https://github.com/fastapi/fastapi/issues/101",
        },
        {
            "id": 2,
            "number": 102,
            "title": "Assigned Issue (should be filtered)",
            "state": "open",
            "assignee": {"login": "dev2"},
            "pull_request": None,
        },
        {
            "id": 3,
            "number": 103,
            "title": "PR (should be filtered)",
            "state": "open",
            "assignee": None,
            "pull_request": {"url": "https://api.github.com/repos/fastapi/fastapi/pulls/103"},
        },
    ]

    route = respx.get("https://api.github.com/repos/fastapi/fastapi/issues").respond(
        status_code=200,
        json=mock_issues,
        headers={"ETag": '"etag-12345"'},
    )

    issues = await client.fetch_repo_issues("fastapi", "fastapi", per_page=10)
    assert len(issues) == 1
    assert issues[0]["number"] == 101

    # Second request returns 304 Not Modified -> returns cached
    respx.get("https://api.github.com/repos/fastapi/fastapi/issues").respond(
        status_code=304,
    )
    cached_issues = await client.fetch_repo_issues("fastapi", "fastapi", per_page=10)
    assert len(cached_issues) == 1
    assert cached_issues[0]["number"] == 101


@pytest.mark.asyncio
@respx.mock
async def test_scraper_orchestrator_pipeline(db_session):
    """Test full orchestrator execution end-to-end with mock API responses."""
    respx.get(url__regex=r"https://api.github.com/repos/.*").respond(
        status_code=200,
        json=[
            {
                "id": 10,
                "number": 55,
                "title": "FastAPI Dependency Injection Bug",
                "body": "Traceback:\n  File \"fastapi/routing.py\", line 10\nFunding on Polar: $150",
                "state": "open",
                "assignee": None,
                "pull_request": None,
                "user": {"login": "tester"},
                "labels": [{"name": "bug"}],
                "created_at": "2026-08-01T12:00:00Z",
                "updated_at": "2026-08-01T12:00:00Z",
                "html_url": "https://github.com/fastapi/fastapi/issues/55",
            }
        ],
    )
    respx.get(url__regex=r"https://api.github.com/search/issues.*").respond(
        status_code=200,
        json={"items": []},
    )

    client = GitHubClient(base_url="https://api.github.com")
    orchestrator = ScraperOrchestrator(client=client)

    result = await orchestrator.scrape_and_index_all(
        session=db_session,
        limit_per_repo=1,
        include_bounty_search=False,
    )

    assert result["indexed_count"] > 0
    assert result["bounties_found"] > 0
    assert len(result["errors"]) == 0
