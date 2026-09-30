"""Environment-driven configuration for the GitScout MCP server."""

from __future__ import annotations

import os


class Settings:
    """Runtime settings, read from environment variables (see .env.example)."""

    # Base URL of the GitScout FastAPI backend, including the /api/v1 prefix.
    api_base: str = os.getenv("GITSCOUT_API_BASE", "http://localhost:8000/api/v1")

    # Streamable HTTP listener. The MCP endpoint is http://{host}:{port}/mcp.
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "9000"))

    # Per-request timeout (seconds). Triage may call an LLM, so keep it generous.
    timeout: float = float(os.getenv("GITSCOUT_TIMEOUT", "60"))


settings = Settings()
