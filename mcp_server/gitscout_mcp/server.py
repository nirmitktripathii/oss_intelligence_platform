"""GitScout MCP server (FastMCP, Streamable HTTP).

Exposes GitScout's issue-intelligence engine as MCP tools. Run it with:

    python -m gitscout_mcp.server

which serves the Streamable HTTP endpoint at http://{MCP_HOST}:{MCP_PORT}/mcp.
The GitScout FastAPI backend must be reachable at GITSCOUT_API_BASE.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.mcpserver import MCPServer

from .client import GitScoutClient
from .config import settings

# MCP SDK 2.x: FastMCP was renamed MCPServer. Host/port are no longer constructor
# args — they are passed to run()/streamable_http_app() at serve time.
mcp = MCPServer(
    "GitScout",
    instructions=(
        "GitScout exposes live open-source issue intelligence. Use search_issues to find "
        "open, unassigned GitHub issues and funded bounties across six engineering domains, "
        "then analyze_issue (or analyze_issue_text for arbitrary issue text) to get an "
        "AST-localized, source-grounded triage: root cause, a minimal reproduction, a "
        "step-by-step fix plan, the repo's contributing rules, and a confidence score. "
        "Always confirm with the user before any action that writes to a repository."
    ),
)


def _issue_row(i: dict) -> dict:
    """Compact, token-friendly projection of an issue for list results."""
    owner, name = i.get("repo_owner", ""), i.get("repo_name", "")
    return {
        "id": i.get("id"),
        "title": i.get("title"),
        "repo": f"{owner}/{name}".strip("/"),
        "url": i.get("url") or i.get("html_url"),
        "domain": i.get("domain"),
        "difficulty": i.get("difficulty"),
        "has_bounty": i.get("has_bounty"),
        "bounty_usd": i.get("bounty_amount_usd"),
        "estimated_hours": i.get("estimated_hours"),
        "hourly_roi": i.get("hourly_roi"),
        "comments": i.get("comments_count"),
        "tech_stack": i.get("tech_stack"),
    }


def _triage_view(t: dict) -> dict:
    """Shape a TriageResponse into the fields an agent needs to act."""
    la = t.get("llm_analysis") or {}
    patch = la.get("patch") or {}
    return {
        "issue_id": t.get("issue_id"),
        "summary": t.get("summary"),
        "confidence": t.get("triage_confidence"),
        "llm_enhanced": t.get("llm_enhanced"),
        "provider": la.get("provider"),
        "root_cause": t.get("root_cause_analysis"),
        "semantic_root_cause": la.get("semantic_root_cause"),
        "localized_files": t.get("localized_files"),
        "reproduction": {
            "language": t.get("reproduction_lang"),
            "instructions": t.get("reproduction_instructions"),
            "code": t.get("reproduction_code"),
        },
        "fix_plan": t.get("fix_plan_steps"),
        "grounded_patch": patch.get("diff_snippet"),
        "regression_risk": patch.get("regression_risk"),
        "contributing": t.get("contributing_guidelines_summary"),
    }


@mcp.tool()
async def search_issues(
    query: str = "",
    domain: Optional[str] = None,
    difficulty: Optional[str] = None,
    tech_stack: Optional[str] = None,
    has_bounty: Optional[bool] = None,
    min_bounty: Optional[float] = None,
    max_hours: Optional[float] = None,
    sort_by: str = "newest",
    limit: int = 10,
) -> dict:
    """Search live, open, unassigned GitHub issues indexed by GitScout.

    Args:
        query: Keyword searched in the title, body, and repository name.
        domain: Engineering domain filter (e.g. "ai_ml", "web", "systems").
        difficulty: Difficulty tier filter (e.g. "Easy", "Medium", "Hard").
        tech_stack: Tech tag(s), comma-separated to match ANY (e.g. "Python,Rust").
        has_bounty: If true, only issues with a funded bounty.
        min_bounty: Minimum bounty amount in USD.
        max_hours: Maximum estimated effort in hours (use to cap time-to-solve).
        sort_by: One of newest, oldest, hourly_roi, bounty_desc, time_asc,
            comments, confidence_desc.
        limit: Max issues to return (1-100).

    Returns a compact list with each issue's id (feed it to analyze_issue),
    repo, bounty, estimated effort, ROI, and tech stack.
    """
    data = await GitScoutClient().list_issues(
        search=query or None,
        domain=domain,
        difficulty=difficulty,
        tech_stack=tech_stack,
        has_bounty=has_bounty,
        min_bounty=min_bounty,
        max_hours=max_hours,
        sort_by=sort_by,
        page=1,
        page_size=max(1, min(limit, 100)),
    )
    items = data.get("items", [])
    return {
        "total_matches": data.get("total"),
        "returned": len(items),
        "issues": [_issue_row(i) for i in items],
    }


@mcp.tool()
async def get_issue(issue_id: str) -> dict:
    """Fetch the full detail of one indexed issue by its GitScout id.

    Args:
        issue_id: GitScout issue id, e.g. "vllm-project/vllm#7890".
    """
    return await GitScoutClient().get_issue(issue_id)


@mcp.tool()
async def analyze_issue(issue_id: str) -> dict:
    """Get GitScout's AI triage for an indexed issue: AST-localized files, a
    source-grounded minimal reproduction, a step-by-step fix plan, the repo's
    contributing rules, and a confidence score. Triage is generated on first
    request if it does not exist yet.

    Args:
        issue_id: GitScout issue id, e.g. "vllm-project/vllm#7890".
    """
    return _triage_view(await GitScoutClient().get_triage(issue_id))


@mcp.tool()
async def analyze_issue_text(
    repo_owner: str,
    repo_name: str,
    title: str,
    body: str = "",
    issue_number: int = 1,
    primary_language: str = "Python",
) -> dict:
    """Run GitScout triage on arbitrary issue text (not necessarily indexed).
    Returns AST localization, a minimal reproduction, and a fix blueprint.

    Args:
        repo_owner: Repository owner/org (e.g. "fastapi").
        repo_name: Repository name (e.g. "fastapi").
        title: Issue title.
        body: Issue body / stack trace (optional but improves localization).
        issue_number: Issue number, if known.
        primary_language: Primary language, drives reproduction scaffolding.
    """
    payload = {
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "issue_number": issue_number,
        "title": title,
        "body": body,
        "primary_language": primary_language,
    }
    return _triage_view(await GitScoutClient().generate_triage(payload))


@mcp.tool()
async def gitscout_health() -> dict:
    """Check that the GitScout backend is reachable and report its telemetry."""
    return await GitScoutClient().health()


def create_app():
    """Return the Streamable HTTP ASGI app (for `uvicorn`/production hosting).

    The endpoint path defaults to /mcp; uvicorn sets the port.
    """
    return mcp.streamable_http_app(host=settings.host)


def main() -> None:
    mcp.run(transport="streamable-http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
