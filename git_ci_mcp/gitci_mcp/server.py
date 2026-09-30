"""Git/CI MCP server (Streamable HTTP).

    python -m gitci_mcp.server      # http://{MCP_HOST}:{MCP_PORT}/mcp

Read-only tools (sandbox_status, show_diff, ci_status) are safe to auto-approve in the agent
planner. Everything else changes a sandbox or GitHub and should stay behind human approval.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.mcpserver import MCPServer

from .config import settings
from .github import GitHub
from .sandbox import GitCiError, SandboxManager

mcp = MCPServer(
    "GitCI",
    instructions=(
        "Turn a triaged issue into a reviewed change. Flow: sandbox_clone, create_branch, apply_patch, "
        "run_tests, show_diff, commit_changes, draft_pr, then ci_status. Only allow-listed repos work. "
        "Pull requests are always drafts and the base branch is never pushed. Ask the user before every "
        "step that writes (clone, patch, tests, commit, PR)."
    ),
)

_sandboxes = SandboxManager(settings)
_github = GitHub(settings)


async def _guard(coro):
    """Turn expected failures into a clean message the agent can relay."""
    try:
        return await coro
    except GitCiError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def sandbox_clone(repo_url: str, ref: Optional[str] = None) -> dict:
    """Clone an allow-listed GitHub repo (https://github.com/owner/repo) into a throwaway sandbox."""
    return await _guard(_sandboxes.create(repo_url, ref))


@mcp.tool()
async def sandbox_status(sandbox_id: str) -> dict:
    """Show the sandbox's branch, uncommitted files and commits ahead of the base branch."""
    return await _guard(_sandboxes.status(sandbox_id))


@mcp.tool()
async def create_branch(sandbox_id: str, name: str) -> dict:
    """Create and switch to a new feature branch in the sandbox."""
    return await _guard(_sandboxes.create_branch(sandbox_id, name))


@mcp.tool()
async def apply_patch(sandbox_id: str, diff: str) -> dict:
    """Apply a unified diff (e.g. GitScout's grounded_patch) to the sandbox. Paths are validated."""
    return await _guard(_sandboxes.apply_patch(sandbox_id, diff))


@mcp.tool()
async def show_diff(sandbox_id: str) -> dict:
    """Show the sandbox's current changes against HEAD (size-capped)."""
    return await _guard(_sandboxes.diff(sandbox_id))


@mcp.tool()
async def run_tests(sandbox_id: str, command: str = "pytest -q") -> dict:
    """Run an allow-listed test command in the sandbox (no shell, time limit, output tail)."""
    return await _guard(_sandboxes.run_tests(sandbox_id, command))


@mcp.tool()
async def commit_changes(sandbox_id: str, message: str) -> dict:
    """Commit all sandbox changes locally under the configured git identity."""
    return await _guard(_sandboxes.commit(sandbox_id, message))


@mcp.tool()
async def ci_status(repo: str, ref: str) -> dict:
    """Read GitHub check-run status for a branch or commit. repo is 'owner/name'."""
    owner, _, name = repo.partition("/")
    if not owner or not name:
        return {"error": "repo must look like owner/name"}
    return await _guard(_github.ci_status(owner, name, ref))


@mcp.tool()
async def draft_pr(sandbox_id: str, title: str, body: str = "") -> dict:
    """Push the sandbox's feature branch and open a DRAFT pull request against the base branch."""
    async def go():
        meta = _sandboxes.meta(sandbox_id)
        pushed = await _sandboxes.push_branch(sandbox_id, settings.github_token)
        pr = await _github.draft_pr(meta["owner"], meta["repo"], pushed["branch"], meta["base"], title, body)
        return {**pr, "branch": pushed["branch"]}
    return await _guard(go())


@mcp.tool()
async def destroy_sandbox(sandbox_id: str) -> dict:
    """Delete a sandbox and everything in it."""
    return await _guard(_sandboxes.destroy(sandbox_id))


def create_app():
    return mcp.streamable_http_app(host=settings.host)


def main() -> None:
    mcp.run(transport="streamable-http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
