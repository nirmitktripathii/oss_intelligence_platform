"""Async HTTP client for the GitScout FastAPI backend.

The MCP server is a thin client over the existing GitScout REST API, so the same
intelligence engine backs the web app and every MCP client. Point it at a local
`uvicorn` instance or the deployed backend via GITSCOUT_API_BASE.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

import httpx

from .config import settings


class GitScoutClient:
    """Minimal async wrapper around the GitScout `/api/v1` endpoints."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.api_base).rstrip("/")
        self.timeout = timeout or settings.timeout

    @staticmethod
    def _encode_id(issue_id: str) -> str:
        # GitScout issue ids look like "owner/repo#123". The route uses a :path
        # converter, so keep the slashes but percent-encode '#' (a URL fragment
        # delimiter) and anything else unsafe.
        return quote(issue_id, safe="/")

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}{path}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, json: dict) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()

    async def list_issues(self, **params: Any) -> dict:
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._get("/issues", clean)

    async def get_issue(self, issue_id: str) -> dict:
        return await self._get(f"/issues/{self._encode_id(issue_id)}")

    async def get_triage(self, issue_id: str) -> dict:
        return await self._get(f"/triage/{self._encode_id(issue_id)}")

    async def generate_triage(self, payload: dict) -> dict:
        return await self._post("/triage/generate", payload)

    async def health(self) -> dict:
        return await self._get("/health")
