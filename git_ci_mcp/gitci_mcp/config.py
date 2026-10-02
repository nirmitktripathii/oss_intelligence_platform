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
    # One pool shared by everyone who uses this server, and nobody can list or free another person's
    # sandbox. So a full pool must free itself: nothing here depends on a caller cleaning up.
    max_sandboxes: int = int(os.getenv("GITCI_MAX_SANDBOXES", "5"))
    # A sandbox nobody has used for this long is deleted the next time one is created.
    sandbox_ttl_seconds: int = int(os.getenv("GITCI_SANDBOX_TTL_SECONDS", "1800"))
    # When the pool is full, the sandbox that has been idle longest is deleted to make room, provided
    # it has been idle at least this long. Anything busier is left alone and the caller is told to wait.
    sandbox_reclaim_seconds: int = int(os.getenv("GITCI_SANDBOX_RECLAIM_SECONDS", "600"))

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
