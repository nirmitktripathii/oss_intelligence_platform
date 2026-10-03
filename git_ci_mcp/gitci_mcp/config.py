"""Environment-driven configuration for the Git/CI MCP server (see .env.example)."""

from __future__ import annotations

import os
import tempfile
from typing import List


def _csv(name: str, default: str) -> List[str]:
    return [p.strip() for p in os.getenv(name, default).split(",") if p.strip()]


class Settings:
    # Streamable HTTP listener. The MCP endpoint is http://{host}:{port}/mcp.
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "9100"))

    # Shared secret the agent backend must present (Authorization: Bearer ...). Required whenever the
    # server listens beyond localhost; see gitci_mcp/auth.py.
    mcp_token: str = os.getenv("GITCI_MCP_TOKEN", "")

    # Every sandbox is a directory under this root; nothing outside it is ever touched.
    sandbox_root: str = os.getenv("GITCI_SANDBOX_ROOT", os.path.join(tempfile.gettempdir(), "gitci-sandboxes"))
    # Live sandboxes (working copies on this machine's disk) across everyone. A ceiling for the disk,
    # not a quota: without one, a single account could clone until the disk fills and the server
    # falls over for everyone.
    max_sandboxes: int = int(os.getenv("GITCI_MAX_SANDBOXES", "15"))
    # Each signed-in user's share of those. One sandbox per branch: opening one past this saves and
    # closes that user's own longest-idle sandbox.
    max_sandboxes_per_user: int = int(os.getenv("GITCI_MAX_SANDBOXES_PER_USER", "5"))
    # A sandbox nobody has used for this long is deleted the next time one is created. A signed-in
    # user's work is saved first (see saved.py), so it comes back on the next sandbox_clone.
    sandbox_ttl_seconds: int = int(os.getenv("GITCI_SANDBOX_TTL_SECONDS", "1800"))
    # When the pool is full, the sandbox that has been idle longest is deleted (saved first) to make
    # room, provided it has been idle at least this long. Otherwise the caller is told to wait.
    sandbox_reclaim_seconds: int = int(os.getenv("GITCI_SANDBOX_RECLAIM_SECONDS", "600"))
    # A sandbox whose work cannot be saved (database down, or its owner out of space) is kept instead
    # of deleted, but only until it has been idle this long, so it cannot hold a slot forever.
    save_grace_seconds: int = int(os.getenv("GITCI_SAVE_GRACE_SECONDS", "86400"))
    # Autosave: this often, every signed-in user's open sandbox is saved if it changed since the last
    # save, so work made between tool calls (a file written by a test run, an edit) is not lost when the
    # server restarts. 0 turns it off. Saving is not use: it never resets a sandbox's idle time.
    autosave_seconds: float = float(os.getenv("GITCI_AUTOSAVE_SECONDS", "60"))
    # One session per branch. A session that resumes a branch takes over the sandbox holding it (that
    # one is saved and closed, and tells its caller so), unless that sandbox was used in the last
    # this many seconds: another session is working on it right now, so the new one is refused and
    # asked to wait or have the other one closed.
    takeover_idle_seconds: int = int(os.getenv("GITCI_TAKEOVER_IDLE_SECONDS", "30"))

    # Where unfinished work is saved. Set GITCI_SAVE_DATABASE_URL (Postgres) on any host whose disk
    # does not survive a restart, such as Render's free plan; without it work is saved under
    # GITCI_SAVE_DIR (default: next to the sandbox root) and lost with the disk.
    save_database_url: str = os.getenv("GITCI_SAVE_DATABASE_URL", "")
    save_dir: str = os.getenv("GITCI_SAVE_DIR", "")
    # Saved work is one record per user, repo and branch. It is deleted after this many days without
    # a change, or as soon as its pull request is merged or closed.
    save_keep_days: int = int(os.getenv("GITCI_SAVE_KEEP_DAYS", "90"))
    # Per branch, and per user in total. A user at either limit cannot start new work until they
    # delete some (delete_saved_work); the database stays a known size however many people sign in.
    max_save_bytes: int = int(os.getenv("GITCI_MAX_SAVE_BYTES", "10000000"))
    max_saved_branches: int = int(os.getenv("GITCI_MAX_SAVED_BRANCHES", "15"))
    max_saved_bytes_per_user: int = int(os.getenv("GITCI_MAX_SAVED_BYTES_PER_USER", "100000000"))

    # Test runs are what use memory and CPU, so they are limited separately. A run waits up to
    # test_queue_seconds for a slot, then the caller is told to try again (the agent gives up on a
    # tool call after 90 seconds, so it cannot wait for long).
    max_concurrent_tests: int = int(os.getenv("GITCI_MAX_CONCURRENT_TESTS", "3"))
    test_queue_seconds: float = float(os.getenv("GITCI_TEST_QUEUE_SECONDS", "20"))

    # Default-deny: only repos owned by these GitHub users/orgs can be cloned, tested or pushed.
    # Point it at your own fork (the demo sandbox), never at repos you do not control, because
    # run_tests executes that repo's code on this machine.
    allowed_owners: List[str] = _csv("GITCI_ALLOWED_OWNERS", "nirmitktripathii")

    # Optional, narrower: when set, only these exact repos ("owner/name") may be used. Use it when
    # many people share the server, so one throwaway repo is the whole blast radius.
    allowed_repos: List[str] = _csv("GITCI_ALLOWED_REPOS", "")

    # Exact commands run_tests may run (argv is split on spaces, no shell).
    test_commands: List[str] = _csv("GITCI_TEST_COMMANDS", "pytest -q,python -m pytest -q,npm test,go test ./...")
    test_timeout_seconds: int = int(os.getenv("GITCI_TEST_TIMEOUT", "180"))
    output_cap_bytes: int = int(os.getenv("GITCI_OUTPUT_CAP", "8000"))
    max_patch_bytes: int = int(os.getenv("GITCI_MAX_PATCH_BYTES", "200000"))

    # Needed only to push and open a draft PR; read-only CI status works without it.
    # Never logged, never put in a remote URL or git config.
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_api: str = os.getenv("GITHUB_API_BASE", "https://api.github.com")

    # Where send_report delivers. The bot token is required. The agent backend (the only caller that
    # holds the bearer token) names the recipient chat, the one the signed-in user linked to their own
    # account; the model never chooses it. TELEGRAM_CHAT_ID is the fallback when no chat is named
    # (a standalone install reporting to its owner). Neither is visible to test commands (see
    # _SAFE_ENV in sandbox.py).
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    # Per chat, and across all chats (the second one bounds the bot's total output).
    report_max_per_hour: int = int(os.getenv("GITCI_REPORTS_PER_HOUR", "10"))
    report_global_max_per_hour: int = int(os.getenv("GITCI_REPORTS_GLOBAL_PER_HOUR", "60"))

    # Commit identity. Unset = use the machine's own git config (your identity).
    author_name: str = os.getenv("GITCI_AUTHOR_NAME", "")
    author_email: str = os.getenv("GITCI_AUTHOR_EMAIL", "")


settings = Settings()
