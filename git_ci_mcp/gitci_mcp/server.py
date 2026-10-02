"""Git/CI MCP server (Streamable HTTP).

    python -m gitci_mcp.server      # http://{MCP_HOST}:{MCP_PORT}/mcp

Read-only tools (sandbox_status, show_diff, ci_status) are safe to auto-approve in the agent
planner. Everything else changes a sandbox or GitHub and should stay behind human approval.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.mcpserver import MCPServer

from .auth import BearerAuthMiddleware, require_token
from .config import settings
from .github import GitHub
from .report import Reporter
from .sandbox import GitCiError, SandboxManager

mcp = MCPServer(
    "GitCI",
    instructions=(
        "Turn a triaged issue into a reviewed change. Flow: sandbox_clone, list_files/read_file, create_branch, edit_file (exact old/new text, preferred) or apply_patch (a unified diff), "
        "run_tests, show_diff, commit_changes, draft_pr, then ci_status and send_report. Only allow-listed repos work. "
        "Pull requests are always drafts and the base branch is never pushed. send_report messages the "
        "user on their linked Telegram chat (the recipient is chosen by the server). A signed-in user's unfinished work is saved "
        "after every change, one record per branch: sandbox_clone lists it, and sandbox_clone with that branch puts it back. "
        "Ask the user before every step that writes (clone, patch, tests, commit, PR, report, deleting saved work)."
    ),
)

_github = GitHub(settings)
_sandboxes = SandboxManager(settings, pr_state=_github.pr_state)
_reporter = Reporter(settings, _sandboxes)


async def _guard(coro):
    """Turn expected failures into a clean message the agent can relay."""
    try:
        return await coro
    except GitCiError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def sandbox_clone(repo_url: str, ref: Optional[str] = None, branch: Optional[str] = None, owner: str = "") -> dict:
    """Clone an allow-listed GitHub repo (https://github.com/owner/repo) into a sandbox. The user's unfinished work is saved after every change, one record per branch. Without branch, the sandbox starts clean and "saved_work" in the result lists the user's saved branches of this repo. To continue one of them, call sandbox_clone with branch set to its name: the work comes back on that branch (see "resumed": commits, changed files, pull request), so continue from there instead of redoing it. The owner is set by the system, not by you."""
    return await _guard(_sandboxes.create(repo_url, ref, user=owner, branch=branch))


@mcp.tool()
async def sandbox_status(sandbox_id: str) -> dict:
    """Show the sandbox's branch, uncommitted files and commits ahead of the base branch."""
    return await _guard(_sandboxes.status(sandbox_id))


@mcp.tool()
async def list_files(sandbox_id: str) -> dict:
    """List the tracked files in the sandbox (read-only)."""
    return await _guard(_sandboxes.list_files(sandbox_id))


@mcp.tool()
async def read_file(sandbox_id: str, path: str) -> dict:
    """Read one text file from the sandbox by repo-relative path (read-only, size-capped). Read a file before writing a patch for it."""
    return await _guard(_sandboxes.read_file(sandbox_id, path))


@mcp.tool()
async def create_branch(sandbox_id: str, name: str) -> dict:
    """Create and switch to a new feature branch in the sandbox, from wherever it is. Created while on another feature branch, it is stacked on that branch, and its pull request targets that branch."""
    return await _guard(_sandboxes.create_branch(sandbox_id, name))


@mcp.tool()
async def apply_patch(sandbox_id: str, diff: str) -> dict:
    """Apply a unified diff (e.g. GitScout's grounded_patch) to the sandbox. Paths are validated."""
    return await _guard(_sandboxes.apply_patch(sandbox_id, diff))


@mcp.tool()
async def edit_file(sandbox_id: str, path: str, old: str, new: str) -> dict:
    """Replace one exact piece of text in a sandbox file. Prefer this over apply_patch for small fixes: copy 'old' exactly from read_file (it must match once), and put the replacement in 'new'."""
    return await _guard(_sandboxes.edit_file(sandbox_id, path, old, new))


@mcp.tool()
async def show_diff(sandbox_id: str) -> dict:
    """Show the sandbox's current changes against HEAD (size-capped)."""
    return await _guard(_sandboxes.diff(sandbox_id))


@mcp.tool()
async def run_tests(sandbox_id: str, command: str = "pytest -q") -> dict:
    """Run an allow-listed test command in the sandbox (no shell, time limit, output tail). Allowed commands: 'pytest -q', 'python -m pytest -q', 'npm test', 'go test ./...' (exact text)."""
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

    async def go():
        _sandboxes.check_repo(owner, name)
        return await _github.ci_status(owner, name, ref)
    return await _guard(go())


@mcp.tool()
async def draft_pr(sandbox_id: str, title: str, body: str = "") -> dict:
    """Push the sandbox's feature branch and open a DRAFT pull request against the base branch (or, for a stacked branch, against the branch it was created on)."""
    async def go():
        meta = _sandboxes.meta(sandbox_id)
        target = await _sandboxes.pr_base(sandbox_id)
        pushed = await _sandboxes.push_branch(sandbox_id, settings.github_token)
        pr = await _github.draft_pr(meta["owner"], meta["repo"], pushed["branch"], target["base"], title, body)
        await _sandboxes.record_pr(sandbox_id, pr["url"])
        out = {**pr, "branch": pushed["branch"], "base": target["base"]}
        if target.get("note"):
            out["note"] = target["note"]
        return out
    return await _guard(go())


@mcp.tool()
async def send_report(title: str, summary: str, pr_url: str = "", chat_id: str = "") -> dict:
    """Send the user a Telegram message about what this mission did. The recipient is chosen by the server, not by you. Give a short title (what was fixed), a summary of what changed and whether the tests passed, and pr_url, the draft pull request link from draft_pr. Send it last, after the pull request exists."""
    return await _guard(_reporter.send(title, summary, pr_url, chat_id))


@mcp.tool()
async def destroy_sandbox(sandbox_id: str, discard: bool = False) -> dict:
    """Delete your sandbox when the task is done. Unfinished work is saved first and comes back with sandbox_clone and its branch. Pass discard=true only when the user says to throw the work away."""
    return await _guard(_sandboxes.destroy(sandbox_id, discard))


@mcp.tool()
async def list_saved_work(repo_url: Optional[str] = None, owner: str = "") -> dict:
    """List the user's saved unfinished work (every repo, or one): branch, commits, changed files, pull request, when saved, and how much of their space (branches and MB) is used. Read-only. The owner is set by the system, not by you."""
    return await _guard(_sandboxes.list_saved(owner, repo_url))


@mcp.tool()
async def delete_saved_work(repo_url: str, branch: str, owner: str = "") -> dict:
    """Permanently delete the user's saved work on one branch, to free space. Only when the user names what to delete. The owner is set by the system, not by you."""
    return await _guard(_sandboxes.delete_saved(owner, repo_url, branch))


def create_app():
    """The ASGI app. With GITCI_MCP_TOKEN set, every request must carry it as a bearer token."""
    require_token(settings.host, settings.mcp_token)
    app = mcp.streamable_http_app(host=settings.host)
    return BearerAuthMiddleware(app, settings.mcp_token) if settings.mcp_token else app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
