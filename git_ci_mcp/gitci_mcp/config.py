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

    # Every sandbox is a directory under this root; nothing outside it is ever touched.
    sandbox_root: str = os.getenv("GITCI_SANDBOX_ROOT", os.path.join(tempfile.gettempdir(), "gitci-sandboxes"))
    max_sandboxes: int = int(os.getenv("GITCI_MAX_SANDBOXES", "3"))
    # Sandboxes older than this are deleted the next time one is created.
    sandbox_ttl_seconds: int = int(os.getenv("GITCI_SANDBOX_TTL_SECONDS", "7200"))

    # Default-deny: only repos owned by these GitHub users/orgs can be cloned, tested or pushed.
    # Point it at your own fork (the demo sandbox), never at repos you do not control, because
    # run_tests executes that repo's code on this machine.
    allowed_owners: List[str] = _csv("GITCI_ALLOWED_OWNERS", "nirmitktripathii")

    # Exact commands run_tests may run (argv is split on spaces, no shell).
    test_commands: List[str] = _csv("GITCI_TEST_COMMANDS", "pytest -q,python -m pytest -q,npm test,go test ./...")
    test_timeout_seconds: int = int(os.getenv("GITCI_TEST_TIMEOUT", "180"))
    output_cap_bytes: int = int(os.getenv("GITCI_OUTPUT_CAP", "8000"))
    max_patch_bytes: int = int(os.getenv("GITCI_MAX_PATCH_BYTES", "200000"))

    # Needed only to push and open a draft PR; read-only CI status works without it.
    # Never logged, never put in a remote URL or git config.
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_api: str = os.getenv("GITHUB_API_BASE", "https://api.github.com")

    # Commit identity. Unset = use the machine's own git config (your identity).
    author_name: str = os.getenv("GITCI_AUTHOR_NAME", "")
    author_email: str = os.getenv("GITCI_AUTHOR_EMAIL", "")


settings = Settings()
