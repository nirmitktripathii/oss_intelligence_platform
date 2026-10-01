"""Tests for prune_closed_issues — the long GitHub sweep must not hold a DB transaction."""

from datetime import datetime, timezone

import httpx
import pytest
import respx
from sqlalchemy import select

from app.models.issue import Issue
from app.models.triage import TriageReport
from app.scrapers.github_client import GitHubClient
from app.scrapers.orchestrator import ScraperOrchestrator

_NOW = datetime(2026, 9, 30, tzinfo=timezone.utc)


def _issue(owner: str, repo: str, number: int) -> Issue:
    return Issue(
        id=f"{owner}/{repo}#{number}",
        repo_owner=owner,
        repo_name=repo,
        issue_number=number,
        title=f"Bug {number}",
        body="Traceback: something broke",
        html_url=f"https://github.com/{owner}/{repo}/issues/{number}",
        author="realuser",
        domain="Web",
        tech_stack=["Python"],
        difficulty="Medium",
        estimated_hours=2.0,
        has_bounty=False,
        state="open",
        comments_count=0,
        labels=[],
        github_created_at=_NOW,
        github_updated_at=_NOW,
        indexed_at=_NOW,
    )


def _github_issue(state: str = "open", assignees=None) -> dict:
    assignees = assignees or []
    return {
        "state": state,
        "pull_request": None,
        "assignee": assignees[0] if assignees else None,
        "assignees": assignees,
    }


async def _seed(db_session) -> None:
    for number in (1, 2, 3, 4):
        db_session.add(_issue("acme", "widget", number))
    db_session.add(
        TriageReport(
            issue_id="acme/widget#1",
            summary="s",
            root_cause_analysis="r",
            localized_files=[],
            reproduction_code="x",
            reproduction_instructions="y",
            fix_plan_steps=[],
        )
    )
    await db_session.commit()


def _mock_github(on_request=None) -> None:
    """#1 closed, #2 deleted (404), #3 assigned, #4 still open and unassigned."""
    responses = {
        1: httpx.Response(200, json=_github_issue(state="closed")),
        2: httpx.Response(404, json={"message": "Not Found"}),
        3: httpx.Response(200, json=_github_issue(assignees=[{"login": "someone"}])),
        4: httpx.Response(200, json=_github_issue()),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if on_request:
            on_request(request)
        return responses[int(request.url.path.rsplit("/", 1)[-1])]

    respx.get(url__regex=r"https://api.github.com/repos/acme/widget/issues/\d+").mock(
        side_effect=handler
    )


@pytest.mark.asyncio
@respx.mock
async def test_prune_closed_removes_stale_issues_and_their_reports(db_session):
    await _seed(db_session)
    _mock_github()

    orchestrator = ScraperOrchestrator(client=GitHubClient(base_url="https://api.github.com"))
    pruned = await orchestrator.prune_closed_issues(db_session)

    assert pruned == 3
    remaining = (await db_session.execute(select(Issue.id))).scalars().all()
    assert remaining == ["acme/widget#4"]
    reports = (await db_session.execute(select(TriageReport))).scalars().all()
    assert reports == []


@pytest.mark.asyncio
@respx.mock
async def test_prune_closed_holds_no_transaction_during_github_sweep(db_session):
    """Regression: the CI crawler held one transaction open for the whole ~15-minute
    sweep; Neon dropped the idle connection and the final commit raised
    PendingRollbackError, discarding every delete. No transaction may be open while
    GitHub is being queried."""
    await _seed(db_session)
    in_txn_during_http = []
    _mock_github(on_request=lambda _req: in_txn_during_http.append(db_session.in_transaction()))

    orchestrator = ScraperOrchestrator(client=GitHubClient(base_url="https://api.github.com"))
    await orchestrator.prune_closed_issues(db_session)

    assert len(in_txn_during_http) == 4
    assert not any(in_txn_during_http)
