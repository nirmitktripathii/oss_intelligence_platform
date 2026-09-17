"""Tests for the ingestion noise filter — only real bugs/features are stored."""

import pytest
import respx
from sqlalchemy import select

from app.models.issue import Issue
from app.scrapers.github_client import GitHubClient
from app.scrapers.noise_filter import NoiseFilter
from app.scrapers.orchestrator import ScraperOrchestrator

# The real-world regression: a Hacker News AI daily digest opened by github-actions[bot]
# in a *-radar repo, which the global bounty search caught because its prose mentions
# "$20K in Bounties". It must never be stored as an issue.
_HN_DIGEST_BODY = (
    "# Hacker News AI 社区动态日报 2026-09-17\n\n"
    "> 数据来源: [Hacker News](https://news.ycombinator.com/) | 共 30 条\n\n"
    "## 1. [Breaking the 1.58-bit Barrier](https://arxiv.org/abs/2609.16338)\n"
    "With 1 Extension: $20K in Bounties from Anthropic, Perplexity, Google, Microsoft\n\n"
    "*本日报由 agents-radar 自动生成。*"
)


def test_hacker_news_digest_rejected():
    ok, reason = NoiseFilter.is_actionable_issue(
        title="📰 Hacker News AI 社区动态日报 2026-09-17",
        body=_HN_DIGEST_BODY,
        author="github-actions[bot]",
        labels=[],
        repo_name="agents-radar",
    )
    assert ok is False
    # Bot author is checked before content, so that's the reason surfaced.
    assert reason == "bot-authored"


def test_bot_author_rejected_even_with_normal_looking_title():
    ok, reason = NoiseFilter.is_actionable_issue(
        title="Update dependencies dashboard",
        body="This is an automated dependency update overview.",
        author="dependabot[bot]",
        repo_name="fastapi",
    )
    assert ok is False
    assert reason == "bot-authored"


def test_english_newsletter_rejected_via_content():
    ok, reason = NoiseFilter.is_actionable_issue(
        title="Weekly digest — top stories this week",
        body="Our newsletter roundup of trending links. This week in open source...",
        author="a-human-editor",
        repo_name="some-project",
    )
    assert ok is False
    assert reason == "digest-or-newsletter"


def test_awesome_list_repo_rejected():
    ok, reason = NoiseFilter.is_actionable_issue(
        title="Add my project to the list",
        body="Please include my tool.",
        author="contributor",
        repo_name="awesome-python",
    )
    assert ok is False
    assert reason == "non-code-repo"


def test_real_bug_is_kept():
    ok, reason = NoiseFilter.is_actionable_issue(
        title="AttributeError in APIRoute endpoint resolution",
        body=(
            "Traceback (most recent call last):\n"
            '  File "fastapi/routing.py", line 180, in get_app\n'
            "AttributeError: 'NoneType' object has no attribute 'app'"
        ),
        author="realuser",
        labels=[{"name": "bug"}],
        repo_name="fastapi",
    )
    assert ok is True
    assert reason is None


def test_single_weak_keyword_does_not_drop_a_real_issue():
    """A bug that merely mentions 'news' or a bounty once stays actionable."""
    ok, reason = NoiseFilter.is_actionable_issue(
        title="Crash when parsing the news feed widget",
        body="The RSS parser throws on empty <item> nodes. There is a $50 bounty.",
        author="realuser",
        repo_name="feedreader",
    )
    assert ok is True
    assert reason is None


def test_empty_item_rejected():
    ok, reason = NoiseFilter.is_actionable_issue(title="", body="", author="realuser")
    assert ok is False
    assert reason == "empty"


@pytest.mark.asyncio
@respx.mock
async def test_orchestrator_skips_bot_digest_from_bounty_search(db_session):
    """End-to-end: a digest returned by the bounty search is never indexed."""
    # Curated-repo fetch returns nothing; the digest comes from the global bounty search.
    respx.get(url__regex=r"https://api.github.com/repos/.*").respond(
        status_code=200, json=[]
    )
    respx.get(url__regex=r"https://api.github.com/search/issues.*").respond(
        status_code=200,
        json={
            "items": [
                {
                    "id": 999,
                    "number": 2281,
                    "title": "📰 Hacker News AI 社区动态日报 2026-09-17",
                    "body": _HN_DIGEST_BODY,
                    "state": "open",
                    "assignee": None,
                    "assignees": [],
                    "pull_request": None,
                    "user": {"login": "github-actions[bot]"},
                    "labels": [],
                    "created_at": "2026-09-17T04:08:05Z",
                    "updated_at": "2026-09-17T04:08:05Z",
                    "html_url": "https://github.com/leisure3318/agents-radar/issues/2281",
                }
            ]
        },
    )

    client = GitHubClient(base_url="https://api.github.com")
    orchestrator = ScraperOrchestrator(client=client)

    result = await orchestrator.scrape_and_index_all(
        session=db_session, limit_per_repo=1, include_bounty_search=True
    )

    assert result["indexed_count"] == 0
    stored = (await db_session.execute(select(Issue))).scalars().all()
    assert stored == []


@pytest.mark.asyncio
async def test_prune_noise_removes_preexisting_digest(db_session):
    """prune_noise purges rows that were stored before the filter existed."""
    from datetime import datetime, timezone

    now = datetime(2026, 9, 17, tzinfo=timezone.utc)
    db_session.add(
        Issue(
            id="leisure3318/agents-radar#2281",
            repo_owner="leisure3318",
            repo_name="agents-radar",
            issue_number=2281,
            title="📰 Hacker News AI 社区动态日报 2026-09-17",
            body=_HN_DIGEST_BODY,
            html_url="https://github.com/leisure3318/agents-radar/issues/2281",
            author="github-actions[bot]",
            domain="Web",
            tech_stack=["Generic"],
            difficulty="Medium",
            estimated_hours=3.5,
            has_bounty=True,
            bounty_amount_usd=20.0,
            state="open",
            comments_count=0,
            labels=[],
            github_created_at=now,
            github_updated_at=now,
            indexed_at=now,
        )
    )
    db_session.add(
        Issue(
            id="fastapi/fastapi#1001",
            repo_owner="fastapi",
            repo_name="fastapi",
            issue_number=1001,
            title="Async dependency cleanup failure",
            body="Traceback: fastapi/dependencies/utils.py line 245",
            html_url="https://github.com/fastapi/fastapi/issues/1001",
            author="realuser",
            domain="Web",
            tech_stack=["Python"],
            difficulty="Medium",
            estimated_hours=2.5,
            has_bounty=False,
            state="open",
            comments_count=0,
            labels=[{"name": "bug"}],
            github_created_at=now,
            github_updated_at=now,
            indexed_at=now,
        )
    )
    await db_session.commit()

    orchestrator = ScraperOrchestrator()
    pruned = await orchestrator.prune_noise(db_session)

    assert pruned == 1
    remaining = (await db_session.execute(select(Issue))).scalars().all()
    assert [i.id for i in remaining] == ["fastapi/fastapi#1001"]
